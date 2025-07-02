FROM jenkins/ssh-agent:latest

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY ./jenkins_agent_keys/id_rsa /home/jenkins/.ssh/id_rsa
COPY ./jenkins_agent_keys/id_rsa.pub /home/jenkins/.ssh/id_rsa.pub
COPY ./jenkins_agent_keys/authorized_keys /home/jenkins/.ssh/authorized_keys

RUN chown jenkins:jenkins -R "/home/jenkins/.ssh" && \
    chown jenkins:jenkins "/home/jenkins/.ssh/id_rsa.pub" && \
    chown jenkins:jenkins "/home/jenkins/.ssh/authorized_keys"
