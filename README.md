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


### Authorize onedrive (update refresh_token outside compose.yml)
Run onedrive from docker compose (with correct permissions to avoid hassle of changing permissions).

First delete old configuration: 

```shell
sudo rm -f .config.backup .config.hash items.sqlite3 refresh_token items.sqlite3-wal .sync_list.hash
```

Do not add any argument or you will change the behaviour of the entrypoint, which sets /onedrive/conf as default
```
docker compose run --remove-orphans -it onedrive
```

You will see the refresh_token file into /onedrive/conf folder. You can cancel with ctrl+c the whole sync, you only need 
to regenerate the token.

Now boot up all containers

```
docker compose up --remove-orphans
```



# Notes
```
ssh-keygen -t ed25519 -C "jenkins@agent" -N "" -f $AGENT_SSH_PRIVATE_KEY_PATH
```

proxy_set_header X-Forwarded-Proto \$scheme;

### Reauth onedrive for token
Every time I need to reauth I spend a lot of time trying to do it. It seems that onedrive ignores my config, but it is 
because the config is not correct and Docker is in the way. 

What I usually do is delete everything in the onedrive_conf (quotes not working rn) folder except the config file. 

Then, ensure that in the config file you have these:

resync = "true"
resync_auth = "true"

After that, run:

docker compose run --remove-orphans onedrive 

### Execute a justification in developer env with params in Sharepoint list
```shell
./venv/bin/python src/main.py --id 159 --input-location service/onedrive_data/Documentació\ Nomines\,\ Seguretat\ Social/input/
```

### Execute a justification in developer env with params in Sharepoint list
```shell
./venv/bin/python src/main.py --naf 08/04135154/70 --begin 2023-01-01 --end 2025-05-31 --author pepito@iciq.es --input local
```