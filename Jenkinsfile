pipeline {
    agent any

    options {
        disableConcurrentBuilds() // Limita a una sola ejecución a la vez
    }

    parameters {
        string(name: 'ID', description: 'Valor obligatorio del parámetro --id')
    }

    environment {
        INPUT_LOCATION = "/home/jenkins/agent/onedrive_data/Documentació Nomines, Seguretat Social/input/"
    }

    stages {
        stage('Validar parámetros') {
            steps {
                script {
                    if (!params.ID?.trim()) {
                        error("El parámetro 'ID' es obligatorio. Deteniendo ejecución.")
                    }
                }
            }
        }

        stage('Preparar entorno Python') {
            steps {
                echo "Creando entorno virtual y actualizando dependencias..."
                sh '''
                    python3 -m venv venv
                    ./venv/bin/pip install --upgrade pip
                    ./venv/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Verificar directorio de entrada') {
            steps {
                echo "Verificando existencia de: ${INPUT_LOCATION}"
                sh '''
	            ls "${INPUT_LOCATION}"
                    if [ ! -d "${INPUT_LOCATION}" ]; then
                        echo "ERROR: No existe el directorio de entrada: ${INPUT_LOCATION}"
                        exit 1
                    fi
                '''
            }
        }

        stage('Ejecutar workflow') {
            steps {
                echo "Lanzando script con --id ${params.ID}"
                sh """
                    ./venv/bin/python3 ./src/main.py \
                      --id "${params.ID}" \
                      --input-location "${INPUT_LOCATION}"
                """
            }
        }
    }
}
