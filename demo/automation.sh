#!/bin/bash

LOG_FILE="/logs/automation.log"
API_URL="http://localhost:5000"
CERT_DIR="/tmp/certs"
CERT_FILE="$CERT_DIR/app.crt"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ---------------------------------------
# Rotation automatique MySQL via Ansible
# ---------------------------------------
auto_rotate() {
    log "Starting automatic MySQL password rotation..."

    response=$(curl -s -X POST "$API_URL/ansible/rotate")

    if echo "$response" | grep -q '"status": "success"'; then
        log "Rotation successful"
    else
        log "Rotation failed: $response"
        exit 1
    fi
}

# -----------------------------------------------------
# Vérification et création du certificat (via Ansible)
# -----------------------------------------------------
check_certs() {
    log "Checking TLS certificates..."

    if [ ! -d "$CERT_DIR" ]; then
        mkdir -p "$CERT_DIR"
        log "Created certificate directory: $CERT_DIR"
    fi

    # si aucun certificat on génére un
    if [ ! -f "$CERT_FILE" ]; then
        log "No certificate found. Generating..."
        curl -s -X POST "$API_URL/ansible/deploy-cert" \
            -H "Content-Type: application/json" \
            -d '{"common_name":"app.local"}' >/dev/null
        log "✅ Certificate generated"
        return
    fi

    # Certificat plus vieux qu'un jour, on le renouvele
    if find "$CERT_FILE" -mtime +1 | grep -q "$CERT_FILE"; then
        log "Certificate is older than 1 day. Renewing..."
        curl -s -X POST "$API_URL/ansible/deploy-cert" \
            -H "Content-Type: application/json" \
            -d '{"common_name":"app.local"}' >/dev/null
        log "✅ Certificate renewed"
    else
        log "Certificate still valid"
    fi
}

# ---------------------------
# Health Check des services
# ---------------------------
health_check() {
    response=$(curl -s "$API_URL/ansible/health")
    log "Health status:"
    echo "$response" | jq '.services'
}

# ---------------------------
# Menu principal
# ---------------------------
case "$1" in
    rotate)
        auto_rotate
        ;;
    cert)
        check_certs
        ;;
    health)
        health_check
        ;;
    all)
        health_check
        auto_rotate
        check_certs
        ;;
    *)
        echo "Usage: $0 {rotate|cert|health|all}"
        exit 1
        ;;
esac

log "Automation complete"
