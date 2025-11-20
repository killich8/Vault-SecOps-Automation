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

def credId = "vault-token"

// Vérifier si le credential existe déjà
def existing = CredentialsProvider.lookupCredentials(
    StringCredentials.class,
    instance,
    null,
    null
).find { it.id == credId }

if (existing != null) {
    println "Credentials '${credId}' already exists, skipping."
} else {
    println "Creating Vault credentials '${credId}'..."

    def vaultToken = new StringCredentialsImpl(
        CredentialsScope.GLOBAL,
        credId,
        "Vault Token for Demo",
        Secret.fromString("root-token-demo")
    )

    store.addCredentials(domain, vaultToken)
    instance.save()

    println "Vault credentials configured"
}
