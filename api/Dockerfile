FROM python:3.9-slim

WORKDIR /app

# --- Installer Ansible + outils nécessaires ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    ansible \
    openssh-client \
    sshpass \
    default-mysql-client \
    curl \
    jq \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# --- Dépendances Python ---
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# --- Code de l'API (app.py, utils.py, vault_client.py, etc.) ---
COPY . /app

# --- Dossiers utiles (même si /logs est monté en volume) ---
RUN mkdir -p /logs /tmp/certs

CMD ["python", "app.py"]
