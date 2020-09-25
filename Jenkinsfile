pipeline {
    agent {label 'linux'}
    triggers {
        cron(env.BRANCH_NAME == 'master' ? 'H/15 8-20 * 1-6 *' : '')
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
			archiveArtifacts artifacts: '*.csv', onlyIfSuccessful: true
            deleteDir()
        }
    }
}