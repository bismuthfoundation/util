#!/bin/bash

# do not run with other cron5, wait 30 sec
sleep 30
python3 latest_1440.py > latest_1440.json
