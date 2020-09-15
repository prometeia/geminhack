pipeline {
  agent any
  stages {
    stage('Synca') {
      steps {
        sh '''pipenv sync

'''
        sh 'pipenv run python -m geminhack.ge2gi mongodb://geminhack:apn2c3578a23x805@erm-pytho-c04.prometeia.lan,erm-pytho-c06.prometeia.lan/geminhack?replicaSet=rsdaa'
      }
    }

  }
}