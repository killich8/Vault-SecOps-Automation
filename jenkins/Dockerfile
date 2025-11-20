FROM jenkins/jenkins:lts

USER root

RUN apt-get update && apt-get install -y \
    curl \
    jq \
    default-mysql-client \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Vault CLI
RUN curl -fsSL https://releases.hashicorp.com/vault/1.13.3/vault_1.13.3_linux_amd64.zip -o vault.zip \
    && unzip vault.zip \
    && mv vault /usr/local/bin/ \
    && rm vault.zip

RUN pip3 install --break-system-packages ansible

USER jenkins

# Plugins Jenkins essentiels
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Auto-config Jenkins (security + Vault credentials)
COPY config/*.groovy /usr/share/jenkins/ref/init.groovy.d/

# Copier les jobs (non montés, intégrés dans l’image)
COPY jobs /usr/share/jenkins/ref/job-configs/
COPY config/*.groovy /usr/share/jenkins/ref/init.groovy.d/
