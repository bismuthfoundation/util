"""
Corrected snapshot_create.py
----------------------------

This version restores historical reward semantics:
- Dev/HN payouts only every 10th block (block % 10 == 0)
- Pre-HF4: real historical mirror reward amounts (8 / 24 / 10×HN)
- Post-HF4: dev + HN completely removed
- Fully compatible with live chain totals and snapshots

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
import connections
from decimal import Decimal
from quantizer import *
from shutil import copyfile


# ---------------------------------------------------------------------
# Fork constants
# ---------------------------------------------------------------------
HF1 = 800_000
HF2 = 1_200_000
HF3 = 1_450_000
HF4 = 4_380_000   # Remove dev + hypernode payouts


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def delete_ledger(filename):
    try:
        os.remove(filename)
    except:
        print(f"No such file {filename} to delete")


def delete_column(db, block_height, column):
    with sqlite3.connect(db) as ledger:
        ledger.text_factory = str
        c = ledger.cursor()
        c.execute(f"DELETE FROM {column} WHERE block_height > ?", (block_height,))
        c.close()


def max_block_height(db):
    with sqlite3.connect(db) as ledger:
        ledger.text_factory = str
        c = ledger.cursor()
        c.execute("SELECT max(block_height) FROM transactions")
        last = c.fetchone()[0]
        c.close()
    return last


def check_integrity(db1, db2):
    ok = True
    with sqlite3.connect(db1) as l:
        l.text_factory = str
        c = l.cursor()
        try:
            c.execute("PRAGMA table_info('transactions')")
            if len(c.fetchall()) != 12:
                ok = False
        except:
            ok = False
        c.close()

    if max_block_height(db1) != max_block_height(db2):
        ok = False

    return ok


def vacuum(db):
    with sqlite3.connect(db) as ledger:
        ledger.text_factory = str
        c = ledger.cursor()
        c.execute("VACUUM")
        c.close()


# ---------------------------------------------------------------------
# Mirror DB writing (dev + hypernode payouts)
# ---------------------------------------------------------------------
def dev_reward(cursor, block_height, timestamp, mining_reward, hn_reward, mirror_hash):
    """
    Insert DEV + HN mirror entries.

    IMPORTANT:
    - Called only every 10th block (matching digest.py)
    - mining_reward and hn_reward are already the *mirror* amounts
      (8, 24, or 10×HN depending on phase)
    - After HF4: return without writing anything
    """
    if block_height >= HF4:
        return

    # Development reward entry
    cursor.execute(
        "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (-block_height,
         timestamp,
         "Development Reward",
         "4edadac9093d9326ee4b17f869b14f1a2534f96f9c5d7b48dc9acaed",
         str(mining_reward),
         "0","0", mirror_hash,
         "0","0","0","0")
    )

    # Hypernode payout entry
    if hn_reward > 0:
        cursor.execute(
            "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (-block_height,
             timestamp,
             "Hypernode Payouts",
             "3e08b5538a4509d9daa99e01ca5912cda3e98a7f79ca01248c2bde16",
             str(hn_reward),
             "0","0", mirror_hash,
             "0","0","0","0")
        )


# ---------------------------------------------------------------------
# Mirror block rebuild (core of correct snapshot generation)
# ---------------------------------------------------------------------
def redo_mirror_blocks(ledgerfile):
    """
    Rebuild dev + HN payouts in static/ledgerfile using *historically correct*
    reward logic, including HF1/HF2/HF3/HF4 behavior.

    This matches the actual chain and all existing mainnet nodes.
    """

    conn = sqlite3.connect("static/" + ledgerfile)
    conn.text_factory = str
    c = conn.cursor()

    # Find highest rounded-down block height
    c.execute("SELECT max(block_height) FROM transactions")
    max_height = c.fetchone()[0]
    max_height = (max_height // 1000) * 1000

    # Remove old mirror entries
    c.execute("DELETE FROM transactions WHERE address='Development Reward'")
    c.execute("DELETE FROM transactions WHERE address='Hypernode Payouts'")

    print(f"Recomputing mirror payouts up to block {max_height}...")

    for bh in range(1, max_height + 1):

        # Dev/HN payouts occur ONLY every 10th block
        if bh % 10 != 0:
            continue

        c.execute(
            "SELECT * FROM transactions WHERE block_height=? ORDER BY rowid",
            (bh,)
        )
        tx_list = c.fetchall()
        if not tx_list:
            continue

        timestamp = tx_list[-1][1]  # timestamp of coinbase tx

        # -------- Historical reward logic --------

        if bh < HF1:
            mining_reward = Decimal(15) - (Decimal(bh) / Decimal(1_000_000))
            hn_reward = Decimal("0.0")

        elif bh <= HF2:
            mining_reward = (
                Decimal(15)
                - Decimal(bh) / Decimal(500_000)
                - Decimal("0.8")
            )
            hn_reward = Decimal("8.0")   # 10 × 0.8

        elif bh < HF3:
            mining_reward = (
                Decimal(15)
                - Decimal(bh) / Decimal(500_000)
                - Decimal("2.4")
            )
            hn_reward = Decimal("24.0")  # 10 × 2.4

        else:
            # BGV linear phase until tail
            mining_reward = Decimal("5.5") - Decimal(bh - HF3) / Decimal("1100000")
            hn_reward = Decimal("10.0") * (
                Decimal("2.4") - (Decimal(bh - HF3 + 5) / Decimal("3000000"))
            )
            if mining_reward < Decimal("0.5"):
                mining_reward = Decimal("0.5")
            if hn_reward < Decimal("0.5"):
                hn_reward = Decimal("0.5")

        # HF4 removal of dev + HN entirely
        if bh >= HF4:
            mining_reward = Decimal("0")
            hn_reward = Decimal("0")

        # -----------------------------------------

        mirror_hash = hashlib.blake2b(str(tx_list).encode(), digest_size=20).hexdigest()
        dev_reward(c, bh, timestamp, mining_reward, hn_reward, mirror_hash)

        if bh % 100_000 == 0:
            print(f"... processed {bh}")

    conn.commit()
    c.close()
    conn.close()


# ---------------------------------------------------------------------
# Main snapshot creation
# ---------------------------------------------------------------------
if __name__ == "__main__":

    app_log = log.log("snapshot.log", "INFO", True)

    # Load config
    with open("snapshot.json") as f:
        config = json.load(f)

    port = 5658
    ledgerfile = "ledger.db"
    indexfile = "index.db"
    tgzfile = "ledger"

    if config.get("testnet") == "True":
        port = 2829
        ledgerfile = "test.db"
        indexfile = "index_test.db"
        tgzfile = "testledger"

    # Stop node
    s = socks.socksocket()
    s.settimeout(10)
    try:
        for _ in range(100):
            s.connect(("127.0.0.1", port))
            connections.send(s, "stop")
            time.sleep(2)
            s.close()
            time.sleep(2)
    except Exception:
        app_log.info("Node stopped")

    time.sleep(6)

    # Recompute mirror payouts
    if config.get("testnet") != "True":
        app_log.info("Redoing mirror blocks")
        redo_mirror_blocks(ledgerfile)
        copyfile("static/hyper.db", config["DB_PATH"] + "hyper.db")

    # Copy DBs to snapshot dir
    copyfile(f"static/{indexfile}", config["DB_PATH"] + indexfile)
    copyfile(f"static/{ledgerfile}", config["DB_PATH"] + ledgerfile)

    block_height = max_block_height(config["DB_PATH"] + ledgerfile)
    app_log.info(f"Restarting node")

    os.system("screen -d -mS node python3 node.py")

    block_height = (block_height // 1000) * 1000
    app_log.info(f"Max block_height = {block_height}")

    # Cleanup older snapshots
    for i in range(3, 10):
        delete_ledger(f"{config['DB_PATH']}{tgzfile}-{block_height-i*1000}.tar.gz")

    # Trim DBs
    delete_column(config["DB_PATH"] + ledgerfile, block_height, "transactions")
    delete_column(config["DB_PATH"] + ledgerfile, block_height, "misc")
    delete_column(config["DB_PATH"] + indexfile, block_height, "aliases")
    delete_column(config["DB_PATH"] + indexfile, block_height, "tokens")

    # Mirror integrity
    if config.get("testnet") != "True":
        delete_column(config["DB_PATH"] + "hyper.db", block_height, "transactions")
        ok = check_integrity(
            config["DB_PATH"] + "hyper.db",
            config["DB_PATH"] + "ledger.db"
        )
    else:
        ok = True

    app_log.info(f"Integrity = {ok}")

    # Build snapshot archive
    if ok:
        app_log.info("Performing vacuum")
        if config.get("testnet") != "True":
            vacuum(config["DB_PATH"] + "hyper.db")
        vacuum(config["DB_PATH"] + indexfile)

        filename = f"{tgzfile}-{block_height}.tar.gz"
        tarpath = config["DB_PATH"] + filename
        tar = tarfile.open(tarpath, "w:gz")
        tar.add(config["DB_PATH"] + indexfile, arcname=indexfile)
        tar.add(config["DB_PATH"] + ledgerfile, arcname=ledgerfile)
        if config.get("testnet") != "True":
            tar.add(config["DB_PATH"] + "hyper.db", arcname="hyper.db")
        tar.close()

        # SHA256
        sha256 = hashlib.sha256()
        with open(tarpath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha256.update(chunk)

        data = {
            "url": config["url"] + filename,
            "filename": filename,
            "timestamp": int(time.time()),
            "sha256": sha256.hexdigest(),
            "block_height": block_height
        }

        with open(config["DB_PATH"] + "ledger.json", "w") as out:
            json.dump(data, out)

