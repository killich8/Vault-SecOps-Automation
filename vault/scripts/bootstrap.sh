#!/usr/bin/env bash
set -e

echo "=== Bootstrap Vault (dev) ==="
sh /scripts/init.sh
sh /scripts/create-secrets.sh
echo "✅ Bootstrap terminé"


# docker-compose up -d
# docker exec vault sh /scripts/bootstrap.sh
