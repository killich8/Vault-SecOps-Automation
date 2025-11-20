#!/bin/bash
# Setup du pipeline dans Jenkins

JENKINS_URL="http://localhost:8090"
JENKINS_USER="admin"
JENKINS_PASS="admin123"

echo "Setting up Jenkins pipeline..."

# Attendre que Jenkins démarre
until curl -s $JENKINS_URL > /dev/null; do
    echo "Waiting for Jenkins..."
    sleep 5
done

# Créer le fichier XML
cat > pipeline-config.xml << 'EOF'
<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <description>SECaaS Automation Pipeline</description>
  <keepDependencies>false</keepDependencies>

  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>@Library('pipeline-library') _
pipeline {
    agent any
    stages {
        stage("Hello") {
            steps {
                echo "Pipeline OK"
            }
        }
    }
}
</script>
    <sandbox>true</sandbox>
  </definition>

  <triggers>
    <hudson.triggers.TimerTrigger>
      <spec>0 */4 * * *</spec>
    </hudson.triggers.TimerTrigger>
  </triggers>
</flow-definition>
EOF

# Créer le job dans Jenkins
curl -X POST "$JENKINS_URL/createItem?name=secops-pipeline" \
    -u "$JENKINS_USER:$JENKINS_PASS" \
    -H "Content-Type: application/xml" \
    -d @pipeline-config.xml

echo "Pipeline created"

# Lancer un premier build
curl -X POST "$JENKINS_URL/job/secops-pipeline/build" \
    -u "$JENKINS_USER:$JENKINS_PASS"

echo "First build triggered"
