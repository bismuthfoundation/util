# Script for uploading a ledger snapshot using AWS
# Script should be run in the main ~/Bismuth folder
# Requires two files: snapshot.json including variable DB_PATH
#                     ledger.json created by snapshot_create.py
#
# To run as a screen job, requires PATH to be defined, for example:
#
# #!/bin/bash
# PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# cd /root/Bismuth
# screen -d -mS aws_upload python3 snapshot_upload.py

import json
import subprocess

with open('snapshot.json') as json_data:
    config = json.load(json_data)

with open("{}/ledger.json".format(config['DB_PATH'])) as json_data:
    data = json.load(json_data)

cmd="aws s3 cp {}{} {} --acl public-read".format(config['DB_PATH'],data['filename'],config['bucket'])
print(cmd)
push=subprocess.Popen(cmd, shell=True)
