"""
Script for generating a blockchain snapshot (backup)
Snapshot block_height is rounded down to nearest 1000 block
Edit the path where the tar.gz file is created in snapshot.json
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
from decimal import *
from quantizer import *
from shutil import copyfile


def delete_ledger(filename):
    try:
        os.remove(filename)
    except:
        print('No such file {} to delete'.format(filename))

def statusget(socket):
    connections.send(s, "statusjson")
    response = connections.receive(s)
    return response


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

def dev_reward(ledger_cursor, block_height, block_timestamp_str, mining_reward, hn_reward, mirror_hash):
    ledger_cursor.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                             (-block_height, block_timestamp_str, "Development Reward", "4edadac9093d9326ee4b17f869b14f1a2534f96f9c5d7b48dc9acaed",
                              str(mining_reward), "0", "0", mirror_hash, "0", "0", "0", "0"))

    ledger_cursor.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                             (-block_height, block_timestamp_str, "Hypernode Payouts", "3e08b5538a4509d9daa99e01ca5912cda3e98a7f79ca01248c2bde16",
                              str(hn_reward), "0", "0", mirror_hash, "0", "0", "0", "0"))


def redo_mirror_blocks(ledgerfile):
    conn = sqlite3.connect('static/' + ledgerfile)
    conn.text_factory = str
    c = conn.cursor()
    print(ledgerfile)
    c.execute("SELECT max(block_height) from transactions;")
    max_height = c.fetchone()[0]

    c.execute("DELETE FROM transactions WHERE address = 'Development Reward'")
    c.execute("DELETE FROM transactions WHERE address = 'Hypernode Payouts'")

    HF = 800000
    HF2 = 1200000
    HF3 = 1450000

    for block_height in range(1,max_height+1):
        if block_height % 10 == 0:
            c.execute("SELECT * FROM transactions WHERE block_height = ? ORDER BY rowid", (block_height,))
            tx_list_to_hash = c.fetchall()
            mining_tx = tx_list_to_hash[-1]
            timestamp = mining_tx[1]

            if block_height < HF:
                mining_reward = 15 - (quantize_eight(block_height) / quantize_eight(1000000))
                hn_reward = 0
            elif block_height <= HF2:
                mining_reward = 15 - (quantize_eight(block_height) / quantize_eight(1000000 / 2)) - Decimal("0.8")
                hn_reward = 8.0
            elif block_height < HF3:
                mining_reward = 15 - (quantize_eight(block_height) / quantize_eight(1000000 / 2)) - Decimal("2.4")
                hn_reward = 24.0
            else:
                mining_reward = 9.7
                if block_height>HF3:
                    mining_reward = quantize_eight(5.5 -(block_height-HF3)/1.1e6)
                hn_reward = quantize_eight(24.0 - (block_height-HF3)/3.0e6)
                if mining_reward < 0:
                    mining_reward = 0

            if block_height % 100000 == 0:
                print(block_height, timestamp, mining_reward)
            mirror_hash = hashlib.blake2b(str(tx_list_to_hash).encode(), digest_size=20).hexdigest()
            dev_reward(c, block_height, timestamp, mining_reward, hn_reward, mirror_hash)

    conn.commit()


if __name__ == "__main__":
    app_log = log.log("snapshot.log", "INFO", True)

    with open('snapshot.json') as json_data:
        config = json.load(json_data)

    port = 5658
    ledgerfile = "ledger.db"
    indexfile = "index.db"
    tgzfile = 'ledger'

    if config['testnet'] == "True":
        port = 2829
        ledgerfile = "test.db"
        indexfile = "index_test.db"
        tgzfile = 'testledger'

    s = socks.socksocket()
    s.settimeout(10)

    try:
        i = 0
        while True and i < 100:
            s.connect(("127.0.0.1", port))
            connections.send(s, "stop")
            time.sleep(2)
            s.close()
            time.sleep(2)
            i += 1

    except Exception as e:
        app_log.info("Node Stopped\n")

    if i<100:
        time.sleep(6)

        if config['testnet'] != "True":
            app_log.info("Redoing mirror blocks")
            redo_mirror_blocks(ledgerfile)
            copyfile("static/hyper.db", config['DB_PATH']+"hyper.db")

        copyfile("static/" + indexfile, config['DB_PATH']+indexfile)
        copyfile("static/" + ledgerfile, config['DB_PATH']+ledgerfile)
        block_height = max_block_height(config['DB_PATH'] + ledgerfile)
        app_log.info("Restarting Node")
        os.system("screen -d -mS node python3 node.py")

        block_height = math.floor(block_height / 1000) * 1000
        app_log.info("Max block_height = {}".format(block_height))

        # Delete old snapshots
        for i in range(3,10):
            delete_ledger(config['DB_PATH'] + tgzfile + '-{}.tar.gz'.format(block_height-i*1000))

        delete_column(config['DB_PATH'] + ledgerfile, block_height, 'transactions')
        delete_column(config['DB_PATH'] + ledgerfile, block_height, 'misc')
        delete_column(config['DB_PATH'] + indexfile, block_height, 'aliases')
        delete_column(config['DB_PATH'] + indexfile, block_height, 'tokens')

        if config['testnet'] == "True":
            bok = True
        else:
            delete_column(config['DB_PATH'] + 'hyper.db', block_height, 'transactions')
            bok = check_integrity(config['DB_PATH'] + 'hyper.db', config['DB_PATH'] + 'ledger.db')

        app_log.info("Integrity = {}".format(bok))

        if bok == True:
            app_log.info("Performing vacuum on dbs")

            if config['testnet'] != "True":
                vacuum(config['DB_PATH'] + 'hyper.db')

            vacuum(config['DB_PATH'] + indexfile)
            #vacuum(config['DB_PATH'] + ledgerfile)
            app_log.info("Creating tar.gz file")
            filename = tgzfile + '-{}.tar.gz'.format(block_height)
            tar = tarfile.open(config['DB_PATH'] + filename, "w:gz")
            tar.add(config['DB_PATH'] + indexfile, arcname=indexfile)
            tar.add(config['DB_PATH'] + ledgerfile, arcname=ledgerfile)
            if config['testnet'] != "True":
                tar.add(config['DB_PATH'] + "hyper.db", arcname='hyper.db')
            tar.close()

            BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
            sha256 = hashlib.sha256()

            with open(config['DB_PATH'] + filename, 'rb') as f:
                while True:
                    data = f.read(BUF_SIZE)
                    if not data:
                        break
                    sha256.update(data)

            url = config['url'] + filename
            data = {'url': url, 'filename': filename, 'timestamp': int(time.time()), 'sha256': sha256.hexdigest(), 'block_height': block_height}
            with open(config['DB_PATH'] + 'ledger.json', 'w') as outfile:
                json.dump(data, outfile)
