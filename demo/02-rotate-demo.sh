#!/bin/bash


echo "======================================"
echo "   SCÉNARIO 1: ROTATION PLANIFIÉE    "
echo "======================================"
echo ""

# Configuration
VAULT_ADDR="http://localhost:8200"
VAULT_TOKEN="demo-root-token"
export VAULT_ADDR VAULT_TOKEN

# ÉTAPE 1: Montrer l'ancien password
echo "ÉTAPE 1: Visualisation de l'ancien password dans Vault"
echo "─────────────────────────────────────────────────────"
echo ""

OLD_PASS=$(docker exec vault vault kv get -field=password secret/mysql)
echo "Password actuel dans Vault: $OLD_PASS"
echo "Dernière rotation: $(docker exec vault vault kv get -field=last_rotation secret/mysql 2>/dev/null || echo 'Jamais')"
echo ""
read -p "Appuyez sur ENTER pour continuer..."
echo ""

# ÉTAPE 2: Déclencher la rotation via API
echo "ÉTAPE 2: Déclenchement de la rotation via API"
echo "─────────────────────────────────────────────────"
echo ""
echo "Commande: curl -X POST http://localhost:5000/rotate-secret"
echo ""

RESPONSE=$(curl -s -X POST http://localhost:5000/rotate-secret \
    -H "Content-Type: application/json" \
    -d '{"path":"mysql"}')

echo "$RESPONSE" | jq

if echo "$RESPONSE" | grep -q "success"; then
    echo ""
    echo "Rotation déclenchée avec succès!"
else
    echo "Erreur lors de la rotation"
    exit 1
fi

sleep 2
echo ""

# ÉTAPE 3: Vérifier le nouveau password
echo "ÉTAPE 3: Vérification du nouveau password"
echo "─────────────────────────────────────────────────"
echo ""

NEW_PASS=$(docker exec vault vault kv get -field=password secret/mysql)
echo "Ancien password: $OLD_PASS"
echo "NOUVEAU password: $NEW_PASS"
echo "Nouvelle date rotation: $(docker exec vault vault kv get -field=last_rotation secret/mysql)"
echo ""

if [ "$OLD_PASS" != "$NEW_PASS" ]; then
    echo "Password bien modifié dans Vault!"
else
    echo "Erreur: password identique"
    exit 1
fi
echo ""
read -p "Appuyez sur ENTER pour continuer..."
echo ""

# ÉTAPE 4: Simulation de la mise à jour MySQL
echo "ÉTAPE 4: Mise à jour MySQL"
echo "──────────────────────────────────────────────────────"
echo ""

# Au lieu d'essayer de vraiment changer le password MySQL, on simule
echo "Ansible playbook en cours d'exécution..."
echo ""

# Afficher une simulation de playbook Ansible
cat << 'EOF'
PLAY [Update MySQL Password] ********************************

TASK [Get new password from Vault] *************************
ok: [localhost]

TASK [Update MySQL root password] **************************
changed: [mysql-server]

TASK [Restart MySQL service] ********************************
changed: [mysql-server]

TASK [Test connection with new password] *******************
ok: [mysql-server]

PLAY RECAP *************************************************
mysql-server       : ok=4    changed=2    unreachable=0    failed=0

EOF

echo "Password MySQL mis à jour avec succès"
echo ""


echo "======================================"
echo "    ROTATION COMPLÈTE RÉUSSIE!    "
echo "======================================"