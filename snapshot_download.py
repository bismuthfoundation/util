"""
Script for selection, download and verification of Bismuth snapshot ledgers
Run the script inside the main Bismuth folder ~/Bismuth
node.py must be stopped when running the script
"""

import sqlite3,base64,hashlib,time,json,requests,tarfile
from quantizer import *
from mining_heavy3 import *
from Cryptodome.Hash import SHA

STEP = 10000 #Print steps
DB_START = 900000
DB_HASH = "cec9b091d8fec7e6208947d17d9b5beaa308e170b9868be52186218f"

def check_dupes(db):
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()

    h3.execute("SELECT * FROM transactions WHERE signature IN (SELECT signature FROM transactions WHERE signature != '0' GROUP BY signature HAVING COUNT(*) >1)")
    results = h3.fetchall()

    allowed_dupes = [708334,708335]

    bok = True
    for result in results:
        if result[0] not in allowed_dupes:
            print ('Duplicate signature in block ' + result[0])
            bok = False

    return bok

def hash_blocks_until(db,n):
    """Returns combined hash of all block hashes in db until block_height n
    """
    sha224 = hashlib.sha224()
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()

    for row in h3.execute("SELECT block_hash FROM transactions where "
            "block_height>-{} and block_height<{} order by block_height asc".format(n,n)):
        sha224.update(str(row[0]).encode("utf-8"))
    return sha224.hexdigest()

def bin_convert(string):
    return ''.join(format(ord(x), '8b').replace(' ', '0') for x in string)

def verify_blocks(db,n):
    """Function for verification of block hashes
    """
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()
        h4 = ledger_check.cursor()

    try:
        h3.execute("SELECT * FROM misc order by block_height desc limit 1")
        db_rows = h3.fetchone()[0]
        print("Number of blocks: {}".format(db_rows))

        print_step = n
        invalid = 0
        db_block_hash_prev = ""
        for row in h3.execute("SELECT * FROM transactions WHERE reward != 0 and "
                "block_height>={} ORDER BY block_height".format(n-1)):
            db_block_height = row[0]
            db_block_hash = str(row[7])
            if db_block_height>=n:
                transaction_list_converted = []
                for transaction in h4.execute("SELECT * FROM transactions WHERE "
                       "block_height={}".format(db_block_height)):
                   q_received_timestamp = quantize_two(transaction[1])
                   received_timestamp = '%.2f' % q_received_timestamp
                   received_address = str(transaction[2])[:56]
                   received_recipient = str(transaction[3])[:56]
                   received_amount = '%.8f' % (quantize_eight(transaction[4]))
                   received_signature_enc = str(transaction[5])[:684]
                   received_public_key_hashed = str(transaction[6])[:1068]
                   received_operation = str(transaction[10])
                   received_openfield = str(transaction[11])

                   transaction_list_converted.append((received_timestamp,
                       received_address, received_recipient,
                       received_amount, received_signature_enc,
                       received_public_key_hashed, received_operation,
                       received_openfield))

                block_hash = hashlib.sha224((str(transaction_list_converted)
                    + db_block_hash_prev).encode("utf-8")).hexdigest()

                if block_hash != db_block_hash:
                    print("Block hash mismatch: {}"
                        .format(db_block_height))
                    invalid = invalid + 1

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

def check_block(block_height_new,miner_address,nonce,db_block_hash,diff0,
    received_timestamp,q_received_timestamp,q_db_timestamp_last):
    """Slightly modified version of Eggdrasyl's function check_block
    """
    if block_height_new == POW_FORK - 1 :
        diff0 = FORK_DIFF
    if block_height_new == POW_FORK:
        diff0 = FORK_DIFF

    bok = False
    real_diff = diffme_heavy3(miner_address,nonce,db_block_hash)
    diff_drop_time = Decimal(180)
    # simplified comparison, no backwards mining
    if real_diff >= int(diff0):
        bok = True

    elif Decimal(received_timestamp) > q_db_timestamp_last + Decimal(diff_drop_time):
        # uses block timestamp, don't merge with diff() for security reasons
        time_difference = q_received_timestamp - q_db_timestamp_last
        diff_dropped = quantize_ten(diff0) + quantize_ten(1) - quantize_ten(time_difference / diff_drop_time)
        # Emergency diff drop
        if Decimal(received_timestamp) > q_db_timestamp_last + Decimal(2 * diff_drop_time):
            factor = 10
            diff_dropped = quantize_ten(diff0) - quantize_ten(1) - quantize_ten(factor
                * (time_difference-2*diff_drop_time) / diff_drop_time)

        if diff_dropped < 50:
            diff_dropped = 50
        if real_diff >= int(diff_dropped):
            bok = True

    return bok

def verify_diff(db):
    """Function for verification of block hashes, starting from block 854660 when Bismuth Heavy was introduced
    """
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()
        h4 = ledger_check.cursor()

    try:
        print("---> Verification of diffs started...")
        mining_open()
        # verify blockchain
        print_step = 854000
        invalid = 0
        db_block_hash_prev = ""
        db_timestamp_prev = ""

        for row in h3.execute('SELECT * FROM misc where block_height>854660 ORDER BY block_height'):
            db_block_height = row[0]
            db_diff = int(float(row[1]))

            h4.execute("SELECT * FROM transactions WHERE block_height = {} and reward != 0".format(db_block_height))
            result = h4.fetchall()[0]
            db_timestamp = quantize_two(result[1])
            miner_address = str(result[2])
            db_block_hash = str(result[7])
            db_nonce = str(result[11])

            if len(db_block_hash_prev)>1:
                bok = check_block(db_block_height,miner_address,db_nonce,db_block_hash_prev,db_diff,db_timestamp,
                    db_timestamp,db_timestamp_prev)

                if not bok:
                    print("Diff mismatch: {}".format(db_block_height))
                    invalid = invalid + 1

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
    """Calculate sha256 hash of file
    """
    buf_size = 65536  # lets read stuff in 64kb chunks!
    sha256 = hashlib.sha256()

    with open(filename, 'rb') as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

def download_file(url, filename):
    """From node.py: Download a file from URL to filename
    :param url: URL to download file from
    :param filename: Filename to save downloaded data as
    returns `filename`
    """
    try:
        r = requests.get(url, stream=True)
        total_size = int(r.headers.get('content-length')) / 1024

        with open(filename, 'wb') as filename:
            chunkno = 0
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    chunkno = chunkno + 1
                    if chunkno % 5e4 == 0:  # every x chunks
                        print("Downloaded {} %".format(int(100 * ((chunkno) / total_size))))

                    filename.write(chunk)
                    filename.flush()
            print("Downloaded 100 %")

        return filename
    except:
        raise

if __name__ == '__main__':
    url='https://hypernodes.bismuth.live/snapshots.json'
    resp = requests.get(url=url)
    data = resp.json()

    print("Functions included from the Mining_Heavy3 module")
    print("Select snapshot number (1-{}) and press ENTER:".format(len(data)))
    i=1
    for site in data:
        print("[{}] Block_height={} url={}".format(i,site['block_height'],site['url']))
        i=i+1

    j=input('Enter your input:')
    j=int(j)-1

    if 0 <= j <len(data):
        ledger = 'static/ledger.tar.gz'
        download_file(data[j]['url'],ledger)

        print("---> Checking file hash (sha256)")
        file_hash = sha256_file(ledger)
        if file_hash != data[j]['sha256']:
            print('---> Incorrect file hash')
        else:
            print("---> Correct file hash")
            print("---> Extracting tar file")
            with tarfile.open(ledger) as tar:
                tar.extractall("static/")

            print("---> Verifying block hashes")
            db_hash = hash_blocks_until('static/ledger.db',DB_START)
            if db_hash != DB_HASH:
                print('---> Incorrect db hash')
            else:
                print('Correct db hash')
                verify_blocks('static/ledger.db',DB_START)
                print("---> Verifying mining difficulties")
                verify_diff('static/ledger.db')
                print("---> Looking for duplicate signatures")
                bok = check_dupes('static/ledger.db')
                if bok:
                    print("No duplicate signatures found")
