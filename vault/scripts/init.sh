#!/bin/bash

VAULT_ADDR="http://localhost:8200"
VAULT_TOKEN="root-token-demo"

export VAULT_ADDR
export VAULT_TOKEN

echo "=== Initialisation Vault ==="

# 1. Activer KV v2 pour les secrets
echo "Activation KV secrets..."
vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV déjà activé"

# 2. Activer PKI pour les certificats
echo "Activation PKI..."
vault secrets enable pki 2>/dev/null || echo "PKI déjà activé"
vault secrets tune -max-lease-ttl=8760h pki

# 3. Générer une CA interne
echo "Création CA..."
vault write -field=certificate pki/root/generate/internal \
    common_name="Demo CA" \
    ttl=8760h > /tmp/CA_cert.crt

# 4. Créer un rôle pour générer des certificats
vault write pki/roles/internal \
    allowed_domains="local,localhost" \
    allow_subdomains=true \
    allow_glob_domains=true \
    max_ttl="720h"

echo "Vault initialisé!"

echo "=== Ajout des policies ==="
vault policy write jenkins /policies/jenkins.hcl
vault policy write automation /policies/automation.hcl