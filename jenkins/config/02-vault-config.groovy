import jenkins.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret

def instance = Jenkins.getInstance()
def domain = Domain.global()
def store = instance
    .getExtensionList('com.cloudbees.plugins.credentials.SystemCredentialsProvider')[0]
    .getStore()


// AppRole Credentials
def roleIdCredId = "vault-role-id"
def secretIdCredId = "vault-secret-id"

def roleId = System.getenv("VAULT_ROLE_ID") ?: ""
def secretId = System.getenv("VAULT_SECRET_ID") ?: ""

// Créer credential pour Role ID
def existingRoleId = CredentialsProvider.lookupCredentials(
    StringCredentials.class, instance, null, null
).find { it.id == roleIdCredId }

if (existingRoleId == null && roleId) {
    println "Creating Vault AppRole Role ID credential..."
    def roleIdCred = new StringCredentialsImpl(
        CredentialsScope.GLOBAL,
        roleIdCredId,
        "Vault AppRole Role ID",
        Secret.fromString(roleId)
    )
    store.addCredentials(domain, roleIdCred)
}

// Créer credential pour Secret ID
def existingSecretId = CredentialsProvider.lookupCredentials(
    StringCredentials.class, instance, null, null
).find { it.id == secretIdCredId }

if (existingSecretId == null && secretId) {
    println "Creating Vault AppRole Secret ID credential..."
    def secretIdCred = new StringCredentialsImpl(
        CredentialsScope.GLOBAL,
        secretIdCredId,
        "Vault AppRole Secret ID",
        Secret.fromString(secretId)
    )
    store.addCredentials(domain, secretIdCred)
}

instance.save()
println "Vault AppRole credentials configured"
