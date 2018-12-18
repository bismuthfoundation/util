"""
Script for uploading a ledger snapshot using AWS
Script should be run in the main ~/Bismuth folder
Requires two files: snapshot.json including variable DB_PATH
                    ledger.json created by snapshot_create.py

Complete script mysnap for snapshot process (between -----):

-----
#!/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd /root/Bismuth
python3 snapshot_create.py
python3 ledger_verify.py
python3 snapshot_upload.py
-----

The script above can be run as a cron entry: 30 19 * * * screen -d -mS mysnap /root/Bismuth/mysnap
"""

import json
import subprocess

with open('snapshot.json') as json_data:
    config = json.load(json_data)

with open("{}/ledger.json".format(config['DB_PATH'])) as json_data:
    data = json.load(json_data)

if data['valid'] == 'valid':
    cmd="aws s3 cp {}{} {} --acl public-read".format(config['DB_PATH'],data['filename'],config['bucket'])
    print(cmd)
    push=subprocess.Popen(cmd, shell=True)
else:
    print('Ledger not validated')
