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
        REGISTRY     = '192.168.0.100:5001'
        IMAGE        = 'family-tree-app'
        CHART_VALUES = 'gitops/charts/api/values.yaml'
    }

    stages {
        stage('Build & Test (Testcontainers)') {
            steps {
                dir('family-tree-app') {
                    sh 'mvn -B -ntp clean verify'
                }
            }
        }

        // ---- CD: build the image and let ArgoCD redeploy via a GitOps tag bump ----
        // Requires (Jenkins/Calculon setup, see gitops/ci/README.md):
        //   * Calculon Docker daemon trusts the insecure registry 192.168.0.100:5001
        //   * a 'github-token' username/password credential with push rights
        //   * the job's Git SCM set to ignore commits from 'Calculon Jenkins' (loop guard)
        stage('Build & Push image') {
            steps {
                script { env.GIT_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim() }
                dir('family-tree-app') {
                    sh 'docker build -t $REGISTRY/$IMAGE:$GIT_SHA -t $REGISTRY/$IMAGE:latest .'
                    sh 'docker push $REGISTRY/$IMAGE:$GIT_SHA'
                    sh 'docker push $REGISTRY/$IMAGE:latest'
                }
            }
        }

        stage('Deploy (GitOps tag bump)') {
            steps {
                // Bump the chart's image.tag to this SHA and commit back; ArgoCD then
                // syncs the new tag. Needs a 'github-token' credential — if it isn't
                // configured yet, skip gracefully ([skip ci] + the loop guard prevent
                // re-triggering once it IS configured).
                script {
                    try {
                        withCredentials([usernamePassword(credentialsId: 'github-token',
                                usernameVariable: 'GH_USER', passwordVariable: 'GH_TOKEN')]) {
                            sh '''
                                sed -i -E "s|^(  tag: ).*|\\1$GIT_SHA|" $CHART_VALUES
                                git config user.email "jenkins@calculon"
                                git config user.name "Calculon Jenkins"
                                git add $CHART_VALUES
                                git commit -m "ci(api): deploy $GIT_SHA [skip ci]" || { echo "image.tag unchanged"; exit 0; }
                                git push https://$GH_USER:$GH_TOKEN@github.com/chrisworth75/dev-familytree.git HEAD:main
                            '''
                        }
                    } catch (err) {
                        echo "Deploy push-back skipped — add the 'github-token' credential to close the GitOps loop. (${err})"
                    }
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
