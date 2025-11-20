import jenkins.model.*
import hudson.security.*

def instance = Jenkins.getInstance()

// Vérifier si un realm est déjà configuré
if (!(instance.getSecurityRealm() instanceof HudsonPrivateSecurityRealm)) {
    println "Configuring security realm..."

    def hudsonRealm = new HudsonPrivateSecurityRealm(false)

    // Créer l'utilisateur admin s'il n'existe pas
    if (hudsonRealm.getUser("admin") == null) {
        hudsonRealm.createAccount("admin", "admin123")
        println "User 'admin' created"
    } else {
        println "User 'admin' already exists"
    }

    instance.setSecurityRealm(hudsonRealm)

    def strategy = new GlobalMatrixAuthorizationStrategy()
    strategy.add(Jenkins.ADMINISTER, "admin")
    instance.setAuthorizationStrategy(strategy)

    instance.save()
    println "Security configured"
} else {
    println "Security realm already configured, skipping."
}
