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
                sh 'conda create -n geminhack python=3.8 -c conda-forge -y'
                sh 'conda install pipenv -n geminhack -c conda-forge -y'
                sh '/opt/jenkins/Miniconda3-4.7.12.1-Linux-x86_64/envs/geminhack/bin/pipenv sync --python /opt/jenkins/Miniconda3-4.7.12.1-Linux-x86_64/envs/geminhack/bin/python3.8'
                sh '/opt/jenkins/Miniconda3-4.7.12.1-Linux-x86_64/envs/geminhack/bin/pipenv run python -m geminhack.ge2gi $GEMINHAACKDB --quotefile=currentsprint.csv'
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'currentsprint.csv', onlyIfSuccessful: true
        }
    }
}