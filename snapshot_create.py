# Script for generating a blockchain snapshot (backup)
# Snapshot block_height is rounded down to nearest 1000 block
# Edit the path where the tar.gz file is created in snapshot.json
# The script takes a while to run, screen job recommended, for example:
# screen -d -mS snapshot python3 ledger_snapshot.py
# Status info is output in file: snapshot.log
# The node is restarted by the script as quickly as possible using:
# screen -d -mS node python3 node.py

import os
import sys
import log
import time
import socks
import math
import json
import sqlite3
import hashlib
import tarfile
import requests
import connections
from shutil import copyfile


def delete_column(db, block_height, column):
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        l = ledger_check.cursor()
        l.execute("DELETE FROM {} where block_height > {}".format(column, block_height))
        l.close()


def max_block_height(db):
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        l = ledger_check.cursor()
        l.execute("SELECT max(block_height) FROM transactions")
        db_block_last = l.fetchone()[0]
        l.close()

    return db_block_last


def check_integrity(db1, db2):
    bok = True
    with sqlite3.connect(db1) as ledger_check:
        ledger_check.text_factory = str
        l = ledger_check.cursor()

        try:
            l.execute("PRAGMA table_info('transactions')")
        except:
            bok = False

        if len(l.fetchall()) != 12:
            bok = False
        l.close()

    db1_block_last = max_block_height(db1)
    db2_block_last = max_block_height(db2)
    if db1_block_last != db2_block_last:
        bok = False

    return bok


def vacuum(db):
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        l = ledger_check.cursor()
        l.execute("vacuum")
        l.close()


if __name__ == "__main__":
    app_log = log.log("snapshot.log", "INFO", True)

    with open('snapshot.json') as json_data:
        config = json.load(json_data)

    s = socks.socksocket()
    s.settimeout(10)

    try:
        i = 0
        while True and i < 100:
            s.connect(("127.0.0.1", 5658))
            connections.send(s, "stop")
            time.sleep(2)
            s.close()
            time.sleep(2)
            i += 1

    except Exception as e:
        app_log.info("Node Stopped\n")

    if i < 100:
        time.sleep(60)
        copyfile("static/index.db", config['DB_PATH']+"index.db")
        copyfile("static/hyper.db", config['DB_PATH']+"hyper.db")
        copyfile("static/ledger.db", config['DB_PATH']+"ledger.db")
        app_log.info("Restarting Node")
        os.system("screen -d -mS node python3 node.py")

        block_height = max_block_height(config['DB_PATH'] + 'hyper.db')
        block_height = math.floor(block_height / 1000) * 1000
        app_log.info("Max block_height = {}".format(block_height))

        delete_column(config['DB_PATH'] + 'hyper.db', block_height, 'transactions')
        delete_column(config['DB_PATH'] + 'ledger.db', block_height, 'transactions')
        delete_column(config['DB_PATH'] + 'ledger.db', block_height, 'misc')
        delete_column(config['DB_PATH'] + 'index.db', block_height, 'aliases')
        delete_column(config['DB_PATH'] + 'index.db', block_height, 'tokens')

        bok = check_integrity(config['DB_PATH'] + 'hyper.db', config['DB_PATH'] + 'ledger.db')
        app_log.info("Integrity = {}".format(bok))

        if bok == True:
            app_log.info("Performing vacuum on dbs")
            vacuum(config['DB_PATH'] + 'index.db')
            vacuum(config['DB_PATH'] + 'hyper.db')
            vacuum(config['DB_PATH'] + 'ledger.db')

            app_log.info("Creating tar.gz file")
            filename = 'ledger-{}.tar.gz'.format(block_height)
            tar = tarfile.open(config['DB_PATH'] + filename, "w:gz")
            tar.add(config['DB_PATH'] + "index.db", arcname='index.db')
            tar.add(config['DB_PATH'] + "hyper.db", arcname='hyper.db')
            tar.add(config['DB_PATH'] + "ledger.db", arcname='ledger.db')
            tar.close()
