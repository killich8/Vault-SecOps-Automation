#!/bin/bash
# Création des secrets de demo

echo "Création des secrets..."

# Secret MySQL
vault kv put secret/mysql \
    password="InitialPassword123!" \
    username="root" \
    host="mysql" \
    port="3306"

# Secret API
vault kv put secret/api \
    token="sk-demo-api-key-12345" \
    endpoint="http://api:5000"

# Secret App
vault kv put secret/app \
    db_password="AppDBPass456" \
    api_key="app-key-789"

echo "Secrets créés"

vault kv list secret/