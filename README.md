# salary-cutter
Program that receives the salaries in a single PDF and cuts the desired page selecting by NAF

# Usage
```shell
sudo apt-get install -y python3 git  # Or similar to install python and git
git clone https://github.com/ICIQ-DMP/salary-cutter
cd salary-cutter
python3 -m venv venv
./venv/bin/pip3 install -r requirements.txt
./venv/bin/python3 ./src/main.py -n 01/12345678-75 -b 2024_06 -e 2025_06
```