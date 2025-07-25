# auto-justifications
Program that implements an automation over the justification of personnel payments (and related documents) in ICIQ. 
Originally, this operation was performed manually with questionable efficiency by the HHRR personnel.  

# Components
* Microsoft 365 list: User interface for interacting with the system. Validates parameters, gathers parameters, shows 
output, keeps historical
* Microsoft Sharepoint: Secure bucket to store the input and output data, which consists in personal data. 
* A3: Indirectly the input data is coming from this service. We will try to skip the step of someone from HHRR 
periodically downloading this data. For that we will need API access. 
* GitHub ICIQ DMP organization: To store the code and secrets of these projects.
* GitHub Actions: To manage and implement workflow.
* GitHub Actions self-hosted runner: Runs in the echempad server. This server is deployed in ICIQ hardware. 

# Workflow



# Usage 
```shell
sudo apt-get install -y python3 git  # Or similar to install python and git
git clone https://github.com/ICIQ-DMP/auto-justifications
cd auto-justifications
python3 -m venv venv
./venv/bin/pip3 install -r requirements.txt
./venv/bin/python3 ./src/main.py --naf 08/04135154/70 --begin 2023-01-01 --end 2025-05-31 --author pepito@iciq.es --input local
```

# Notes
```
ssh-keygen -t ed25519 -C "jenkins@agent" -N "" -f $AGENT_SSH_PRIVATE_KEY_PATH
```

proxy_set_header X-Forwarded-Proto \$scheme;
