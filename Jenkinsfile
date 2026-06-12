// CI for the family tree app. Runs on Calculon (Jenkins + Docker).
// `mvn verify` triggers the Testcontainers integration test, which spins up an
// ephemeral Postgres, lets Flyway build the schema, boots the app, and seeds the
// curated tree through the HTTP API. Relies on system JDK 21 + Maven on PATH and
// the jenkins user being in the docker group (Testcontainers -> /var/run/docker.sock).
pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        // Docker 29+ on the agent dropped API versions < 1.44; the docker-java client
        // bundled with Testcontainers otherwise falls back to 1.32 and gets rejected.
        DOCKER_API_VERSION = '1.44'
    }

    stages {
        stage('Build & Test (Testcontainers)') {
            steps {
                dir('family-tree-app') {
                    sh 'mvn -B -ntp clean verify'
                }
            }
        }
    }

    post {
        always {
            junit testResults: 'family-tree-app/target/surefire-reports/*.xml', allowEmptyResults: true
        }
    }
}
