"""
Script for verification of local Bismuth snapshot ledger
Run the script inside the main Bismuth folder ~/Bismuth
Local node can be running in parallel
"""

import sqlite3, base64, hashlib, time, json, requests, tarfile
from quantizer import *
from mining_heavy3 import *
from Cryptodome.Hash import SHA
from decimal import Decimal

STEP = 10000  # Print steps
DB_START = 900000
# IMPORTANT: database hash (the one you computed for your ledger)
DB_HASH = "6ce0ed5c30b1181a676a2e9c870ae8fdf6f210e518e0f1f6ee923e20"

HF4 = 4_380_000  # soft fork height: dev + HN rewards removed on chain


def check_dupes(db):
    """Look for duplicate signatures in the ledger (except a few allowed cases)."""
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()

        h3.execute("""
            SELECT * FROM transactions
            WHERE signature IN (
                SELECT signature
                FROM transactions
                WHERE signature != '0'
                GROUP BY signature
                HAVING COUNT(*) > 1
            )
        """)
        results = h3.fetchall()

    allowed_dupes = [708334, 708335]

    bok = True
    for result in results:
        if result[0] not in allowed_dupes:
            print('Duplicate signature in block ' + str(result[0]))
            bok = False

    return bok


def hash_blocks_until(db, n):
    """Returns combined SHA224 of all block_hash values in db until block_height n."""
    sha224 = hashlib.sha224()
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()

        for row in h3.execute(
            "SELECT block_hash FROM transactions "
            "WHERE block_height > -? AND block_height < ? "
            "ORDER BY block_height ASC",
            (n, n),
        ):
            sha224.update(str(row[0]).encode("utf-8"))

    return sha224.hexdigest()


def bin_convert(string):
    return ''.join(format(ord(x), '8b').replace(' ', '0') for x in string)


def verify_blocks(db, n):
    """Verification of block hashes from height n onward."""
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()
        h4 = ledger_check.cursor()

        try:
            h3.execute("SELECT * FROM misc ORDER BY block_height DESC LIMIT 1")
            db_rows = h3.fetchone()[0]
            print("Number of blocks: {}".format(db_rows))

            print_step = n
            invalid = 0
            db_block_hash_prev = ""

            for row in h3.execute(
                "SELECT * FROM transactions WHERE reward != 0 "
                "AND block_height >= ? ORDER BY block_height",
                (n - 1,),
            ):
                db_block_height = row[0]
                db_block_hash = str(row[7])

                if db_block_height >= n:
                    transaction_list_converted = []
                    for transaction in h4.execute(
                        "SELECT * FROM transactions WHERE block_height = ?",
                        (db_block_height,),
                    ):
                        q_received_timestamp = quantize_two(transaction[1])
                        received_timestamp = '%.2f' % q_received_timestamp
                        received_address = str(transaction[2])[:56]
                        received_recipient = str(transaction[3])[:56]
                        received_amount = '%.8f' % (quantize_eight(transaction[4]))
                        received_signature_enc = str(transaction[5])[:684]
                        received_public_key_hashed = str(transaction[6])[:1068]
                        received_operation = str(transaction[10])
                        received_openfield = str(transaction[11])

                        transaction_list_converted.append((
                            received_timestamp,
                            received_address,
                            received_recipient,
                            received_amount,
                            received_signature_enc,
                            received_public_key_hashed,
                            received_operation,
                            received_openfield
                        ))

                    block_hash = hashlib.sha224(
                        (str(transaction_list_converted) + db_block_hash_prev).encode("utf-8")
                    ).hexdigest()

                    if block_hash != db_block_hash:
                        print("Block hash mismatch: {}".format(db_block_height))
                        invalid += 1

                db_block_hash_prev = db_block_hash

                if db_block_height > print_step:
                    print("Block hashes, verified {}".format(print_step))
                    print_step += STEP

            if invalid == 0:
                print("All blocks in the local ledger are valid")
            else:
                print("{} invalid blocks found".format(invalid))

            h3.close()
            h4.close()

        except Exception as e:
            print("Error: {}".format(e))
            raise


def check_block(block_height_new, miner_address, nonce, db_block_hash, diff0,
                received_timestamp, q_received_timestamp, q_db_timestamp_last):
    """
    Verify that a block's heavy3 PoW meets the stored difficulty.

    Simplified: no legacy POW_FORK / FORK_DIFF constants.
    """
    bok = False
    real_diff = diffme_heavy3(miner_address, nonce, db_block_hash)
    diff_drop_time = Decimal(180)

    # Normal case
    if real_diff >= int(diff0):
        bok = True

    # Time-based emergency diff adjustment
    elif Decimal(received_timestamp) > q_db_timestamp_last + Decimal(diff_drop_time):
        time_difference = q_received_timestamp - q_db_timestamp_last
        diff_dropped = (
            quantize_ten(diff0)
            + quantize_ten(1)
            - quantize_ten(time_difference / diff_drop_time)
        )

        # Emergency diff drop
        if Decimal(received_timestamp) > q_db_timestamp_last + Decimal(2 * diff_drop_time):
            factor = 10
            diff_dropped = (
                quantize_ten(diff0)
                - quantize_ten(1)
                - quantize_ten(factor * (time_difference - 2 * diff_drop_time) / diff_drop_time)
            )

        if diff_dropped < 50:
            diff_dropped = 50

        if real_diff >= int(diff_dropped):
            bok = True

    return bok


def verify_diff(db):
    """Verification of difficulty values starting from heavy3 introduction."""
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()
        h4 = ledger_check.cursor()

        try:
            print("---> Verification of diffs started...")
            mining_open()  # from mining_heavy3

            print_step = 854000
            invalid = 0
            db_block_hash_prev = ""
            db_timestamp_prev = ""

            for row in h3.execute(
                "SELECT * FROM misc WHERE block_height > 854660 ORDER BY block_height"
            ):
                db_block_height = row[0]
                db_diff = int(float(row[1]))

                h4.execute(
                    "SELECT * FROM transactions "
                    "WHERE block_height = ? AND reward != 0",
                    (db_block_height,),
                )
                result = h4.fetchall()[0]
                db_timestamp = quantize_two(result[1])
                miner_address = str(result[2])
                db_block_hash = str(result[7])
                db_nonce = str(result[11])

                if len(db_block_hash_prev) > 1:
                    bok = check_block(
                        db_block_height,
                        miner_address,
                        db_nonce,
                        db_block_hash_prev,
                        db_diff,
                        db_timestamp,
                        db_timestamp,
                        db_timestamp_prev,
                    )

                    if not bok:
                        print("Diff mismatch: {}".format(db_block_height))
                        invalid += 1

                if db_block_height > print_step:
                    print("Bismuth diffs, verified {}".format(print_step))
                    print_step += STEP

                db_block_hash_prev = db_block_hash
                db_timestamp_prev = db_timestamp

            if invalid == 0:
                print("All diffs in the local ledger are valid")
            else:
                print("{} invalid diffs found".format(invalid))

            h3.close()
            h4.close()

        except Exception as e:
            print("Error: {}".format(e))
            raise


def sha256_file(filename):
    """Calculate sha256 hash of file."""
    buf_size = 65536
    sha256 = hashlib.sha256()

    with open(filename, 'rb') as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def download_file(url, filename):
    """Download a file from URL to filename."""
    try:
        r = requests.get(url, stream=True)
        total_size = int(r.headers.get('content-length')) / 1024

        with open(filename, 'wb') as filename_obj:
            chunkno = 0
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    chunkno += 1
                    if chunkno % 5e4 == 0:
                        print("Downloaded {} %".format(int(100 * (chunkno / total_size))))
                    filename_obj.write(chunk)
                    filename_obj.flush()
            print("Downloaded 100 %")

        return filename
    except:
        raise


def check_post_hf4_rewards(db, hf4=HF4):
    """
    HF4-specific sanity check:
    Ensure there are NO dev / hypernode mirror payouts for blocks >= HF4.

    Mirror entries use negative block_height: -real_block_height.
    So real blocks >= HF4 correspond to block_height <= -HF4.
    """
    limit = -hf4

    with sqlite3.connect(db) as conn:
        conn.text_factory = str
        c = conn.cursor()

        # Dev rewards after HF4?
        c.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE address = 'Development Reward'
              AND block_height <= ?
        """, (limit,))
        dev_count = c.fetchone()[0]

        # HN payouts after HF4?
        c.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE address = 'Hypernode Payouts'
              AND block_height <= ?
        """, (limit,))
        hn_count = c.fetchone()[0]

    if dev_count or hn_count:
        print(
            f"ERROR: Found dev/HN rewards after HF4 (>= {hf4}): "
            f"dev={dev_count}, hn={hn_count}"
        )
        return False

    print(f"HF4 economics OK: no dev/HN mirror rewards for blocks >= {hf4}")
    return True


if __name__ == '__main__':
    print("Functions included from the mining_heavy3 module")
    print("Verifying static/ledger.db")

    print("---> Verifying block hashes")
    db_hash = hash_blocks_until('static/ledger.db', DB_START)
    print(f"---> db hash is: {db_hash}")

    if db_hash != DB_HASH:
        print('---> WARNING: db hash does not match anchor (expected {}, got {})'.format(DB_HASH, db_hash))
        # You can choose to return/exit here if you want strict anchoring.

    # Deep checks (you can gate these under the DB_HASH match if you prefer strict mode)
    verify_blocks('static/ledger.db', DB_START)
    print("---> Verifying mining difficulties")
    verify_diff('static/ledger.db')
    print("---> Looking for duplicate signatures")
    bok = check_dupes('static/ledger.db')
    if bok:
        print("No duplicate signatures found")
    print("---> Checking HF4 reward removal (no dev/HN after 4,380,000)")
    check_post_hf4_rewards('static/ledger.db')
