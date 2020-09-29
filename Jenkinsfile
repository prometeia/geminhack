pipeline {
    agent {label 'geminhack'}
    triggers {
        cron("TZ=Europe/Rome\nH/15 8-20 * * 1-6")
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
        }
    }
}
