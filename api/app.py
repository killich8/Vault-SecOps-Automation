from flask import Flask, jsonify, request, Response
import hvac
import os
import random
import string
from datetime import datetime
from flask_cors import CORS
import subprocess
import json
import requests
import time
import glob
import threading

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# =============================
# Vault AppRole Authentication
# =============================
def create_vault_client():
    """Crée un client Vault authentifié via AppRole."""
    vault_addr = os.getenv("VAULT_ADDR", "http://vault:8200")
    role_id = os.getenv("VAULT_ROLE_ID")
    secret_id = os.getenv("VAULT_SECRET_ID")

    if not role_id or not secret_id:
        raise RuntimeError(
            "[Vault] VAULT_ROLE_ID et VAULT_SECRET_ID sont requis. "
            "Exécutez le bootstrap Vault et configurez les variables d'environnement."
        )

    client = hvac.Client(url=vault_addr)

    auth_response = client.auth.approle.login(
        role_id=role_id,
        secret_id=secret_id
    )
    print(f"[Vault] Authentifié via AppRole (token TTL: {auth_response['auth']['lease_duration']}s)")
    return client

# Client Vault global
vault_client = create_vault_client()

# Renouvellement automatique du token AppRole
def renew_token_periodically():
    """Renouvelle le token Vault avant expiration."""
    while True:
        time.sleep(1800)  
        try:
            if vault_client.is_authenticated():
                vault_client.auth.token.renew_self()
                print("[Vault] Token renouvelé")
        except Exception as e:
            print(f"[Vault] Erreur renouvellement: {e}")
            # Recréer le client si le renouvellement échoue
            global vault_client
            vault_client = create_vault_client()

# Démarrer le thread de renouvellement
renewal_thread = threading.Thread(target=renew_token_periodically, daemon=True)
renewal_thread.start()


# Métriques Prometheus
rotation_counter = Counter(
    'vault_rotation_total',
    'Total rotations performed',
    ['status', 'path']
)

rotation_duration = Histogram(
    'vault_rotation_duration_seconds',
    'Rotation duration in seconds'
)

active_certificates = Gauge(
    'vault_active_certificates',
    'Number of active certificates'
)

last_rotation = Gauge(
    'vault_last_rotation_timestamp',
    'Unix timestamp of last successful rotation'
)

cert_expiration = Gauge(
    'vault_certificate_expiration_seconds',
    'Unix timestamp when certificate expires',
    ['common_name']
)

api_requests = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint']
)

def count_active_certificates():
    """
    Compter les certificats actifs.
    Pour la démo : on compte les fichiers .crt dans /tmp/certs
    (là où ton playbook Ansible les stocke).
    """
    cert_files = glob.glob('/tmp/certs/*.crt')
    return len(cert_files)



def record_rotation(path: str, success: bool, start_time: float):
    """Met à jour les métriques de rotation (Prometheus)."""
    duration = time.time() - start_time
    status_label = 'success' if success else 'failure'

    rotation_counter.labels(status=status_label, path=path).inc()
    rotation_duration.observe(duration)

    if success:
        last_rotation.set(time.time())


@app.route('/metrics')
def metrics():
    """Endpoint Prometheus metrics"""
    data = generate_latest()
    return Response(data, mimetype=CONTENT_TYPE_LATEST)


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
@app.route('/health')
def health():
    api_requests.labels(method='GET', endpoint='/health').inc()

    try:
        vault_ok = vault_client.is_authenticated()
        certs_count = count_active_certificates()

        try:
            last_rot = last_rotation._value.get()
        except Exception:
            last_rot = 0.0

        return jsonify({
            'status': 'healthy' if vault_ok else 'degraded',
            'vault_connected': vault_ok,
            'metrics': {
                'active_certificates': certs_count,
                'last_rotation_timestamp': last_rot
            }
        })
    except Exception:
        return jsonify({'status': 'error'}), 500



@app.route('/rotate-secret', methods=['POST'])
def rotate_secret():
    api_requests.labels(method='POST', endpoint='/rotate-secret').inc()
    start_time = time.time()

    data = request.get_json() or {}
    path = data.get('path', 'mysql')

    try:
        # lire l'ancien secret
        old_secret = vault_client.secrets.kv.v2.read_secret_version(
            path=path
        )
        old_data = old_secret['data']['data']

        # générer le nouveau password
        chars = string.ascii_letters + string.digits + "!@#$"
        new_password = ''.join(random.choices(chars, k=16))

        old_data['password'] = new_password
        old_data['last_rotation'] = datetime.now().isoformat()
        old_data['rotated_by'] = 'api'

        # sauvegarder dans Vault
        vault_client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=old_data
        )

        # METRICS
        rotation_counter.labels(status='success', path=path).inc()
        rotation_duration.observe(time.time() - start_time)
        last_rotation.set(time.time())

        return jsonify({
            'status': 'success',
            'path': path,
            'message': f'Password rotated for {path}'
        })

    except Exception as e:
        rotation_counter.labels(status='failure', path=path).inc()
        rotation_duration.observe(time.time() - start_time)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/metrics/log-rotation', methods=['POST'])
def log_rotation():
    """Log rotation metrics from external sources (Jenkins, Ansible)"""
    api_requests.labels(method='POST', endpoint='/metrics/log-rotation').inc()

    data = request.get_json() or {}
    path = data.get('path', 'mysql')
    status = data.get('status', 'success')
    source = data.get('source', 'external')

    rotation_counter.labels(status=status, path=path).inc()
    if status == 'success':
        last_rotation.set(time.time())

    return jsonify({
        'status': 'logged',
        'path': path,
        'source': source
    })


@app.route('/generate-cert', methods=['POST'])
def generate_cert():
    """Générer un certificat via Vault PKI"""
    api_requests.labels(method='POST', endpoint='/generate-cert').inc()

    data = request.get_json() or {}
    common_name = data.get('common_name', 'app.local')


    ttl = data.get("ttl", "24h")

    payload = {
        "common_name": common_name,
        "ttl": ttl
    }
    try:
        response = vault_client.write(
            'pki/issue/internal',
            common_name=common_name,
            ttl=ttl
        )

        cert_data = response['data']

        # Sauvegarder le cert localement
        os.makedirs('/tmp/certs', exist_ok=True)
        crt_path = f"/tmp/certs/{common_name}.crt"
        with open(crt_path, 'w') as f:
            f.write(cert_data['certificate'])

        # je recalcule le nombre de certificats actifs
        active_certificates.set(count_active_certificates())

        # enregistrer l'expiration du certificat
        cert_expiration.labels(common_name=common_name).set(cert_data['expiration'])
    
        return jsonify({
            'status': 'success',
            'common_name': common_name,
            'serial_number': cert_data['serial_number'],
            'certificate': cert_data['certificate'][:200] + '...',
            'expiration': cert_data['expiration'],
            'ttl_used': ttl
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ------------------
# Endpoints Ansible
# ------------------
@app.route("/ansible/rotate", methods=["POST"])
def ansible_rotate():
    """Rotation via Ansible"""
    api_requests.labels(method='POST', endpoint='/ansible/rotate').inc()
    start_time = time.time()

    path = 'mysql_ansible'

    result = run_ansible_playbook('rotate-mysql')

    if result['success']:
        # log prometheus via ansible too
        record_rotation(path=path, success=True, start_time=start_time)

        return jsonify({
            'status': 'success',
            'message': 'MySQL password rotated via Ansible'
        })
    else:

        record_rotation(path=path, success=False, start_time=start_time)

        return jsonify({
            'status': 'error',
            'message': 'Rotation failed',
            'error': result['stderr']
        }), 500


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
        active_certificates.set(count_active_certificates())

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
        
        jenkins_base = "http://jenkins:8080/jenkins"

        # here I use session to maintain cookies
        session = requests.Session()
        session.auth = ('admin', 'admin123')

        # Get Jenkins crumb (CSRF token)
        crumb_url = f"{jenkins_base}/crumbIssuer/api/json"
        crumb_response = session.get(crumb_url)

        if crumb_response.status_code != 200:
            return jsonify({
                'status': 'error',
                'message': 'Crumb fetch failed',
                'code': crumb_response.status_code
            }), 500

        crumb = crumb_response.json()['crumb']

        # Trigger Jenkins Job
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
