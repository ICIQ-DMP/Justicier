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

# Some notes
The code is not my best code. I have many instructions and functions that repeat because they are not designed properly. 
But it works. If you have to maintain this software start by refactoring and defining function that can be reused. Work 
using data models and abstractions. There are many already created, but they can be improved, refactored and expanded to
include more abstractions such as a PDF file, the different types of documents that we are working with or some metadata
structures such as the data structure for the requests.



```
docker run \
  -v $(pwd)/service/onedrive_conf:/onedrive/conf \
  -v $(pwd)/service/onedrive_data:/onedrive/data \
  -v $(pwd)/service/onedrive_logs:/onedrive/logs \
  -e ONEDRIVE_DOWNLOADONLY=1 \
  -e ONEDRIVE_CLEANUPLOCAL=1 \
  -l io.containers.autoupdate=image \
  --restart unless-stopped \
  --health-cmd "sh -c '[ -s /onedrive/conf/items.sqlite3-wal ]'" \
  --health-interval 60s \
  --health-retries 2 \
  --health-timeout 5s \
  -it docker.io/driveone/onedrive:edge
```

# Notes
```
ssh-keygen -t ed25519 -C "jenkins@agent" -N "" -f $AGENT_SSH_PRIVATE_KEY_PATH
```

proxy_set_header X-Forwarded-Proto \$scheme;

### Reauth onedrive for token
docker compose run --entrypoint "onedrive --reauth" -v ./service/onedrive_conf:/onedrive/conf onedrive 
cp ./service/onedrive_conf/refresh_token secrets/ONEDRIVE_TOKEN


./venv/bin/python src/main.py --id 159 --input-location service/onedrive_data/Documentació\ Nomines\,\ Seguretat\ Social/input/