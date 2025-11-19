from flask import Flask, jsonify, request
import hvac
import os
import random
import string
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Connection Vault
vault_client = hvac.Client(
    url=os.getenv('VAULT_ADDR', 'http://vault:8200'),
    token=os.getenv('VAULT_TOKEN', 'root-token-demo')
)

@app.route('/health')
def health():
    """Endpoint de santé"""
    try:
        return jsonify({
            'status': 'healthy',
            'vault_connected': vault_client.is_authenticated(),
            'timestamp': datetime.now().isoformat()
        })
    except:
        return jsonify({'status': 'error'}), 500

@app.route('/rotate-secret', methods=['POST'])
def rotate_secret():
    """Rotation d'un secret"""
    data = request.get_json() or {}
    path = data.get('path', 'mysql')
    
    # Générer nouveau password (16 caractères)
    chars = string.ascii_letters + string.digits + "!@#$"
    new_password = ''.join(random.choices(chars, k=16))
    
    try:
        # Lire l'ancien secret
        old_secret = vault_client.secrets.kv.v2.read_secret_version(
            path=path
        )
        old_data = old_secret['data']['data']
        
        # Mettre à jour avec nouveau password
        old_data['password'] = new_password
        old_data['last_rotation'] = datetime.now().isoformat()
        
        # Sauvegarder
        vault_client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=old_data,
            mount_point="secret"
        )
        
        return jsonify({
            'status': 'success',
            'path': path,
            'message': f'Password rotated for {path}'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/generate-cert', methods=['POST'])
def generate_cert():
    """Générer un certificat"""
    data = request.get_json() or {}
    common_name = data.get('common_name', 'app.local')
    
    try:
        # Générer via PKI Vault
        response = vault_client.write(
            'pki/issue/internal',
            common_name=common_name,
            ttl='24h'
        )
        
        cert_data = response['data']
        
        return jsonify({
            'status': 'success',
            'common_name': common_name,
            'serial_number': cert_data['serial_number'],
            'certificate': cert_data['certificate'][:200] + '...',  # Tronqué pour la démo
            'expiration': cert_data['expiration']
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)