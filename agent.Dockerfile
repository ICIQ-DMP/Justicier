FROM jenkins/ssh-agent:latest

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i '/es_ES.UTF-8/s/^# //' /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=es_ES.UTF-8

ENV LANG=es_ES.UTF-8
ENV LANGUAGE=es_ES:es
ENV LC_ALL=es_ES.UTF-8

COPY ./jenkins_agent_keys/id_rsa /home/jenkins/.ssh/id_rsa
COPY ./jenkins_agent_keys/id_rsa.pub /home/jenkins/.ssh/id_rsa.pub
COPY ./jenkins_agent_keys/authorized_keys /home/jenkins/.ssh/authorized_keys

RUN chown jenkins:jenkins -R "/home/jenkins/.ssh" && \
    chown jenkins:jenkins "/home/jenkins/.ssh/id_rsa.pub" && \
    chown jenkins:jenkins "/home/jenkins/.ssh/authorized_keys"
