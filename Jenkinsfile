pipeline {
    agent {label 'linux'}
    triggers {
        cron(env.BRANCH_NAME == 'master' ? 'H/15 * * * *' : '')
    }
    options {
      buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    stages {
        stage('Synca') {
            steps {
                sh 'chmod u+x gegirun.sh;./gegirun.sh'
            }
        }
    }
    post {
        always {
			archiveArtifacts artifacts: 'currentsprint.csv', onlyIfSuccessful: true
            deleteDir()
        }
    }
}