from flask import Flask, jsonify, request
import hvac
import os
import random
import string
from datetime import datetime
from flask_cors import CORS
import subprocess
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# 🔐 Connexion à Vault
vault_client = hvac.Client(
    url=os.getenv("VAULT_ADDR", "http://vault:8200"),
    token=os.getenv("VAULT_TOKEN", "root-token-demo")
)


# -----------------------------
# Helper Ansible
# -----------------------------
def run_ansible_playbook(playbook_name, extra_vars=None):
    """
    Exécute un playbook Ansible présent dans /ansible/playbooks/<name>.yml
    Retourne: {success: bool, stdout: str, stderr: str}
    """
    cmd = [
        "ansible-playbook",
        "-i", "/ansible/inventory/hosts.ini",
        f"/ansible/playbooks/{playbook_name}.yml",
        "-v",
    ]

    if extra_vars:
        # On passe les extra_vars en JSON pour éviter les galères de quoting
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


# -----------------------------
# Endpoints existants
# -----------------------------
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
    Body JSON:
      { "path": "mysql" }  -> correspond à secret/mysql
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
    Body JSON:
      { "common_name": "app.local" }
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


# -----------------------------
# Endpoints Ansible
# -----------------------------
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

    # Si le playbook lui-même plante
    if not result["success"]:
        return jsonify({
            "status": "error",
            "message": "Health check playbook failed",
            "error": result["stderr"],
        }), 500

    services = {"vault": None, "api": None, "mysql": None}

    # On parcourt TOUT le stdout Ansible et on cherche les lignes de debug
    for line in result["stdout"].splitlines():
        line = line.strip()
        # Exemple de lignes réelles :
        # "Vault: UP",
        # "API: UP",
        # "MySQL: DOWN"
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
        "raw_stdout": result["stdout"],   # utile pour debug, tu pourras le supprimer après
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
