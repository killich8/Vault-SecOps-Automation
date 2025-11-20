import jenkins.model.*
import hudson.model.*
import java.nio.file.*

def jenkins = Jenkins.getInstance()
def jobName = "rotate-mysql"
def jobsDir = new File("/usr/share/jenkins/ref/jobs/${jobName}")

// Si le job existe déjà, on ignore
if (jenkins.getItem(jobName) != null) {
    println "Job '${jobName}' already exists, skipping."
    return
}

println "Creating job '${jobName}'..."

jobsDir.mkdirs()

// Copier le config.xml depuis l'image
def sourceConfig = new File("/usr/share/jenkins/ref/jobs/rotate-mysql-config.xml")
def targetConfig = new File(jobsDir, "config.xml")

Files.copy(sourceConfig.toPath(), targetConfig.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING)

jenkins.reload()

println "Job '${jobName}' created successfully."
