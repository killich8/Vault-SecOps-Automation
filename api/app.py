from flask import Flask, jsonify, request
import hvac
import os
import random
import string
from datetime import datetime
from flask_cors import CORS
import subprocess
import json
import requests

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Connexion à Vault
vault_client = hvac.Client(
    url=os.getenv("VAULT_ADDR", "http://vault:8200"),
    token=os.getenv("VAULT_TOKEN", "root-token-demo")
)


# ----------------
# Helper Ansible
# ----------------
def run_ansible_playbook(playbook_name, extra_vars=None):
    """
    Exécute un playbook Ansible présent dans /ansible/playbooks/
    Retourne: {success: bool, stdout: str, stderr: str}
    """
    cmd = [
        "ansible-playbook",
        "-i", "/ansible/inventory/hosts.ini",
        f"/ansible/playbooks/{playbook_name}.yml",
        "-v",
    ]

    if extra_vars:
        cmd.extend(["-e", json.dumps(extra_vars)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# --------------------
# Endpoints existants
# --------------------
@app.route("/health")
def health():
    """Health API + check Vault"""
    try:
        return jsonify(
            {
                "status": "healthy",
                "vault_connected": vault_client.is_authenticated(),
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/rotate-secret", methods=["POST"])
def rotate_secret():
    """
    Rotation d'un secret KV dans Vault.
    """
    data = request.get_json() or {}
    path = data.get("path", "mysql")

    chars = string.ascii_letters + string.digits + "!@#$"
    new_password = "".join(random.choices(chars, k=16))

    try:
        old_secret = vault_client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point="secret",
        )
        old_data = old_secret["data"]["data"]

        old_data["password"] = new_password
        old_data["last_rotation"] = datetime.now().isoformat()

        vault_client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=old_data,
            mount_point="secret",
        )

        return jsonify(
            {
                "status": "success",
                "path": f"secret/{path}",
                "message": f"Password rotated for secret/{path}",
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/generate-cert", methods=["POST"])
def generate_cert():
    """
    Générer un certificat via PKI Vault.
    """
    data = request.get_json() or {}
    common_name = data.get("common_name", "app.local")

    try:
        response = vault_client.write(
            "pki/issue/internal",
            common_name=common_name,
            ttl="24h",
        )

        cert_data = response["data"]

        return jsonify(
            {
                "status": "success",
                "common_name": common_name,
                "serial_number": cert_data["serial_number"],
                "certificate": cert_data["certificate"][:200] + "...",
                "expiration": cert_data.get("expiration"),
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ------------------
# Endpoints Ansible
# ------------------
@app.route("/ansible/rotate", methods=["POST"])
def ansible_rotate():
    """
    Rotation MySQL via Ansible (playbook rotate-mysql.yml)
    """
    result = run_ansible_playbook("rotate-mysql")

    if result["success"]:
        return jsonify(
            {
                "status": "success",
                "message": "MySQL password rotated via Ansible",
            }
        )
    else:
        return jsonify(
            {
                "status": "error",
                "message": "Rotation failed",
                "error": result["stderr"],
            }
        ), 500


@app.route("/ansible/deploy-cert", methods=["POST"])
def ansible_deploy_cert():
    """
    Génération + déploiement d'un certificat via Ansible
    (playbook deploy-cert.yml)
    Body JSON:
      { "common_name": "app.local" }
    """
    data = request.get_json() or {}
    common_name = data.get("common_name", "app.local")

    result = run_ansible_playbook("deploy-cert", {"common_name": common_name})

    if result["success"]:
        return jsonify(
            {
                "status": "success",
                "message": f"Certificate deployed for {common_name}",
            }
        )
    else:
        return jsonify(
            {
                "status": "error",
                "message": "Certificate deployment failed",
                "error": result["stderr"],
            }
        ), 500


@app.route("/ansible/health", methods=["GET"])
def ansible_health():
    """Health check via Ansible"""
    result = run_ansible_playbook("check-health")

    if not result["success"]:
        return jsonify({
            "status": "error",
            "message": "Health check playbook failed",
            "error": result["stderr"],
        }), 500

    services = {"vault": None, "api": None, "mysql": None}

    for line in result["stdout"].splitlines():
        line = line.strip()
        if "Vault:" in line:
            services["vault"] = "UP" in line
        elif "API:" in line:
            services["api"] = "UP" in line
        elif "MySQL:" in line:
            services["mysql"] = "UP" in line

    return jsonify({
        "status": "success",
        "services": services,
        "timestamp": datetime.now().isoformat(),
        "raw_stdout": result["stdout"],
    })


# ------------------
# Jenkins
# ------------------
@app.route('/webhook/trigger-jenkins', methods=['POST'])
def trigger_jenkins():
    data = request.get_json() or {}
    job_name = data.get('job', 'rotate-mysql')

    try:
        # URLs internes Docker
        jenkins_base = "http://jenkins:8080/jenkins"

        # Use session to maintain cookies
        session = requests.Session()
        session.auth = ('admin', 'admin123')

        # 1. Get Jenkins crumb (CSRF token)
        crumb_url = f"{jenkins_base}/crumbIssuer/api/json"
        crumb_response = session.get(crumb_url)

        if crumb_response.status_code != 200:
            return jsonify({
                'status': 'error',
                'message': 'Crumb fetch failed',
                'code': crumb_response.status_code
            }), 500

        crumb = crumb_response.json()['crumb']

        # 2. Trigger Jenkins Job
        build_url = f"{jenkins_base}/job/{job_name}/build"

        response = session.post(
            build_url,
            params={'token': 'trigger-token'},
            headers={'Jenkins-Crumb': crumb}
        )

        if response.status_code in [200, 201]:
            return jsonify({
                'status': 'success',
                'message': f'Job {job_name} triggered',
                'jenkins_response': response.status_code
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed triggering job',
                'code': response.status_code
            }), 500

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    

@app.route('/webhook/jenkins-callback', methods=['POST'])
def jenkins_callback():
    data = request.get_json() or {}

    # Log
    with open('/logs/jenkins-events.log', 'a') as f:
        f.write(f"{datetime.now().isoformat()} - Jenkins: {json.dumps(data)}\n")

    phase = data.get('build', {}).get('phase')
    status = data.get('build', {}).get('status')
    number = data.get('build', {}).get('number')

    if phase == 'COMPLETED':
        if status == 'SUCCESS':
            print(f"Build #{number} finished successfully.")
        else:
            print(f"Build #{number} FAILED.")

    return jsonify({'status': 'received'})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
