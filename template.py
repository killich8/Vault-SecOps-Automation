#!/usr/bin/env python3
import os

FILES = [
    # Root
    "README.md",
    "Makefile",
    "docker-compose.yml",
    ".env",
    ".gitignore",
    
    # Vault
    "vault/config/vault-dev.hcl",
    "vault/policies/jenkins.hcl",
    "vault/policies/automation.hcl",
    "vault/scripts/init.sh",
    "vault/scripts/setup-pki.sh",
    "vault/scripts/create-secrets.sh",
    
    # API
    "api/app.py",
    "api/requirements.txt",
    "api/Dockerfile",
    "api/vault_client.py",
    "api/utils.py",
    
    # Ansible
    "ansible/ansible.cfg",
    "ansible/inventory/hosts.ini",
    "ansible/playbooks/rotate-mysql.yml",
    "ansible/playbooks/deploy-cert.yml",
    "ansible/playbooks/check-health.yml",
    "ansible/files/rotate.sh",
    
    # Jenkins
    "jenkins/Dockerfile",
    "jenkins/jobs/rotate-job.xml",
    "jenkins/pipelines/Jenkinsfile",
    
    # Monitoring
    "monitoring/prometheus/prometheus.yml",
    "monitoring/grafana/datasources.yml",
    "monitoring/grafana/dashboards/vault.json",
    "monitoring/exporters/metrics.py",
    
    # Dashboard
    "dashboard/index.html",
    "dashboard/style.css",
    "dashboard/app.js",
    
    # Demo
    "demo/01-init.sh",
    "demo/02-rotate-demo.sh",
    "demo/03-cert-demo.sh",
    "demo/04-incident.sh",
    
    # Docs
    "docs/MEP.md",
    "docs/RUN.md",
    "docs/ARCHITECTURE.md",
    
    # Logs
    "logs/.gitkeep"
]

# Créer structure
for filepath in FILES:
    # Créer dossier si nécessaire
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    
    open(filepath, 'a').close()
    
    if filepath.endswith('.sh'):
        os.chmod(filepath, 0o755)
    
    print(f" {filepath}")

print("\n Structure créée!")