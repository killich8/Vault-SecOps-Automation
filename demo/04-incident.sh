#!/bin/bash
# demo-scenario-2.sh

echo "======================================"
echo "  SCÉNARIO
: INCIDENT CERTIFICAT    "
echo "======================================"
echo ""

# PRÉPARATION: Créer un certificat qui va bientôt expirer
echo "Préparation: Création d'un certificat proche expiration"
echo "──────────────────────────────────────────────────────────"
echo ""

# Générer un certificat avec TTL court (pour simulation)
docker exec vault vault write pki/issue/internal \
    common_name="api.local" \
    ttl="1h" > /tmp/cert-demo.json

SERIAL=$(cat /tmp/cert-demo.json | grep serial_number | cut -d'"' -f4)
echo "Certificat créé avec serial: $SERIAL"
echo "Expire dans 1 heure"
read -p "Appuyez sur ENTER pour continuer..."
echo ""

# ÉTAPE 1: Alerte Prometheus
echo "Alerte Prometheus détectée"
echo "───────────────────────────────────────"
echo ""
echo "ALERTE: CertificateExpiringSoon"
echo "Severity: WARNING"
echo "Message: Certificate for api.local expires in < 24h"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"

# l'alerte dans les logs
echo "[$(date)] ALERT: Certificate expiring soon - api.local" >> /tmp/alerts.log

read -p "Appuyez sur ENTER pour déclencher le pipeline Jenkins automatique..."
echo ""

# ÉTAPE 2: Jenkins déclenche le pipeline
echo "Jenkins déclenche automatiquement le pipeline"
echo "──────────────────────────────────────────────────────"

echo ""
echo "Pipeline #127 démarré..."
sleep 2
echo ""

# ÉTAPE 3: Génération nouveau certificat
echo "ÉTAPE 3: Génération automatique du nouveau certificat"
echo "────────────────────────────────────────────────────"
echo ""

RESPONSE=$(curl -s -X POST http://localhost:5000/generate-cert \
    -H "Content-Type: application/json" \
    -d '{"common_name":"api.local"}')

echo "$RESPONSE" | jq

NEW_SERIAL=$(echo "$RESPONSE" | jq -r '.serial_number')
echo ""
echo "Nouveau certificat généré!"
echo "   Serial: $NEW_SERIAL"
echo ""
read -p "Appuyez sur ENTER pour continuer..."
echo ""
sleep 2
# ÉTAPE 4: Déploiement automatique
echo "ÉTAPE 4: Déploiement automatique via Ansible"
echo "───────────────────────────────────────────────"
echo ""
sleep 2
# Simuler le déploiement Ansible
cat << EOF
PLAY [Deploy certificate] **********************************

TASK [Copy certificate to servers] ************************
changed: [api.local]

TASK [Reload services] *************************************
changed: [api.local]


PLAY RECAP ************************************************
api.local       : ok=2    changed=2    unreachable=0    failed=0

EOF


echo "Certificat a bien été déployé "

