"""
Run this script in the main ~/Bismuth folder
If ledger is valid, data['valid'] = 'valid' in ledger.json
Log stored in verify.log
"""

import sqlite3
import base64
import hashlib
import time
import json
import log
from quantizer import *
from mining_heavy3 import *
from Cryptodome.Hash import SHA
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import PKCS1_v1_5
from polysign.signerfactory import SignerFactory

POW_FORK = 854600
HF2 = 1200000
HF3 = 1450000

def verify_txs(app_log, db, full_ledger):
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()

    try:
        app_log.info("Blockchain verification started...")
        # verify blockchain
        h3.execute("SELECT Count(*) FROM transactions")
        db_rows = h3.fetchone()[0]
        app_log.info("Number of transactions: {}".format(db_rows))

        # verify genesis
        if full_ledger:
            h3.execute("SELECT block_height, recipient FROM transactions WHERE block_height = 1")
            result = h3.fetchall()[0]
            genesis = result[1]
            app_log.info("Genesis: {}".format(genesis))

        db_hashes = {
            '27258-1493755375.23': 'acd6044591c5baf121e581225724fc13400941c7',
            '27298-1493755830.58': '481ec856b50a5ae4f5b96de60a8eda75eccd2163',
            '30440-1493768123.08': 'ed11b24530dbcc866ce9be773bfad14967a0e3eb',
            '32127-1493775151.92': 'e594d04ad9e554bce63593b81f9444056dd1705d',
            '32128-1493775170.17': '07a8c49d00e703f1e9518c7d6fa11d918d5a9036',
            '37732-1493799037.60': '43c064309eff3b3f065414d7752f23e1de1e70cd',
            '37898-1493799317.40': '2e85b5c4513f5e8f3c83a480aea02d9787496b7a',
            '37898-1493799774.46': '4ea899b3bdd943a9f164265d51b9427f1316ce39',
            '38083-1493800650.67': '65e93aab149c7e77e383e0f9eb1e7f9a021732a0',
            '52233-1493876901.73': '29653fdefc6ca98aadeab37884383fedf9e031b3',
            '52239-1493876963.71': '4c0e262de64a5e792601937a333ca2bf6d6681f2',
            '52282-1493877169.29': '808f90534e7ba68ee60bb2ea4530f5ff7b9d8dea',
            '52308-1493877257.85': '8919548fdbc5093a6e9320818a0ca058449e29c2',
            '52393-1493877463.97': '0eba7623a44441d2535eafea4655e8ef524f3719',
            '62507-1493946372.50': '81c9ca175d09f47497a57efeb51d16ee78ddc232',
            '70094-1494032933.14': '2ca4403387e84b95ed558e7c9350c43efff8225c',
            '107579-1495499385.55': '4c01d491b35583e6a880a016bd08ac992b25e946',
            '109032-1495581934.71': 'e81caa48f4e04272b764bc58a0a68e07e44e50be',
            '109032-1495581968.35': '26419351bc5cea781ac4b41c6a5ea757585ddbe4',
            '109032-1495581997.74': 'ad634a23b69b6d5cf8514d6e3a5d8c7311240b58',
            '109032-1495582052.39': '9a5815e1aaa50c129fad05d9502b2b83518ab0c6',
            '109032-1495582073.80': 'c3ecbc412ed82539f866d5ce95a46df8f1bbc992',
            '109032-1495582093.85': 'eff64357d0320c77c7774bdffbf0032bfbbcf40a',
            '109032-1495582137.48': 'e3f34c3b0608a2276c3d179fe2091ae3b5b33458',
            '109032-1495582167.81': 'dd9cf2436672c2b2b5a6cc230fe0bf548d3856c9',
            '109032-1495582188.16': '978f7e42a98d00dd0b520fa330aec136976f2b10',
            '109032-1495582212.49': '7991d2efed6c21509d104c4bb9a41db873a186bf',
            '109032-1495582261.99': '496491a8243f92ef216b308a4b8e160f9ac8902f',
            '109032-1495582281.92': 'c3eb75f099546cd1afec051194a4f0ce72808811',
            '109032-1495582326.49': 'f6a2d15c18692c1507a2f0f31fb98ed126f6285d',
            '109032-1495582345.66': 'c61b3073ae3345146589ef31a565874f3506aa3b',
            '109032-1495582362.29': '91f0c2eb7c7d8badf279130f9d8810c31bca0738',
            '109032-1495582391.27': '86ba22a36ad1604fcbeccb7b53a4f1878e42e7c8',
            '109032-1495582414.48': '6c7fb968c6df05e6c41a2b57417265fcd21cf049',
            '109032-1495582431.57': '85b846479fcf65e0b0407ae5a62a43e548a05b0f',
            '109032-1495582452.90': 'be5985949a9f9c05e1087c373179f4699c9a285b',
            '109032-1495582474.30': '5f8f33ccd3861dbaf3a9de679b2c57bb4dc6aa9e',
            '109032-1495582491.33': 'bbca4c2cfb3b073dc26e2882a0c635b4f545c796',
            '109032-1495582519.66': 'e8acaf4c324ad6380e95f05b5488507c1f677f0d',
            '109032-1495582552.33': '1d19efbe74f1dcc0f3eecc97e57602a854cee80c',
            '109032-1495582566.89': '6f855517a5a15764275b6b473df3d8b0424e14ca',
            '109032-1495582578.06': '55d4af749af916a4af4190106133c4bd618fccd8',
            '109032-1495582590.27': '312009efa7d8fbf3bd788704b9f4f9f4cca2bf6b',
            '109032-1495582605.78': '92dd15a93e5fdc6d419e40e73c738618830778bf',
            '109032-1495582629.72': 'c90a2baeeffb8283a781787af1b9a2d4e7390768',
            '109032-1495582650.66': '76919616b3b26a13fbfccdb1f6a70478ecc99f5b',
            '109032-1495582673.69': '8228a29ec46f4c017c983073e4bf52306d30a20e',
            '109032-1495582692.76': 'd7f83c9cda72380748c9e697e864e64f371b0c87',
            '109032-1495582705.82': 'd87f74eaa82d2566129d45f0040c6a796e6c00d6',
            '109032-1495582718.75': '41e4b6595ecc0087b7a370c08b9e911ddf70621e',
            '109032-1495582731.23': '11b95e7f210e616a39f1f3fc67055fed34d06d58',
            '109032-1495582743.92': '118bcaf2a4064b64d1f48aaae2382ad9505027a4',
            '109032-1495582756.92': '67a81e040ebf257024b56bf99de5763079d9c38b',
            '109032-1495582768.07': '0afbcd111bedf61f67ee5eafc2e2792991254f33',
            '109032-1495582780.58': 'd7351ae8a29e27327fc0952ce27405be487d4dcf',
            '109032-1495582793.76': '56eca3202795443669b35af18c316a0bdc0166ab',
            '109032-1495582810.24': '4841f3f01cd986863110fc9e61622c3598d7f6c4',
            '109032-1495582823.22': '7a4244e0549fc2da9fa15328506f5afeb7fc36f4',
            '109032-1495582833.89': '7af9fc46b2d70c5070737c0a1ecaccac11f420dd',
            '109032-1495582860.55': 'eb8742ae1ec649e01b5ca5064da52b8be75a0be1',
            '109034-1495582892.79': 'ef00516b9f723fe7eeed98465a2521f1d1910189',
            '109034-1495582904.05': '56172b6625a163cd1e90e7676b33774b30dbe9a6',
            '109034-1495582915.38': '90290d53ff8f16ffa9cf8ca5add1f155612dbefe',
            '109035-1495582926.98': '8c5fc98e23948df56e9c05acc73e0f8f18df176e',
            '109035-1495582943.53': '8c6ececc083b4fcadac2022f815407c685a7fcaf',
            '109035-1495582976.65': '4cf4d45d0c98be3f1a8553f5ff2d183770ec1d27',
            '109035-1495583322.14': '8d1c49a5c3e029a3c420a5361f3ed0ef629a3e91'
        }

        print_step = 10000
        invalid = 0
        for row in h3.execute('SELECT * FROM transactions WHERE block_height > 0 and reward = 0 ORDER BY block_height'):

            db_block_height = str(row[0])
            db_timestamp = '%.2f' % (quantize_two(row[1]))
            db_address = str(row[2])[:56]
            db_recipient = str(row[3])[:56]
            db_amount = '%.8f' % (quantize_eight(row[4]))
            db_signature_enc = str(row[5])[:684]
            db_public_key_hashed = str(row[6])[:1068]
            db_operation = str(row[10])[:30]
            db_openfield = str(row[11])  # no limit for backward compatibility
            buffer = str((db_timestamp, db_address, db_recipient, db_amount, db_operation, db_openfield)).encode("utf-8")

            try:
                SignerFactory.verify_bis_signature(db_signature_enc, db_public_key_hashed, buffer, db_address)
            except Exception as e:
                hash = SHA.new(buffer)
                try:
                    if hash.hexdigest() != db_hashes[db_block_height + "-" + db_timestamp]:
                        app_log.warning("Signature validation problem: {}".format(db_block_height))
                        invalid = invalid + 1
                except Exception as e:
                    app_log.warning("Signature validation problem: {}".format(db_block_height))
                    invalid = invalid + 1

            if int(db_block_height) > print_step:
                app_log.info("Bismuth transactions verified, block = {}".format(print_step))
                print_step += 10000

        if invalid == 0:
            app_log.info("All transactions in the local ledger are valid")
        else:
            app_log.warning("{} invalid transactions found".format(invalid))

        h3.close()

    except Exception as e:
        app_log.error("Error: {}".format(e))
        raise

    return invalid


def bin_convert(string):
    return ''.join(format(ord(x), '8b').replace(' ', '0') for x in string)


def verify_blocks(app_log, db):
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()
        h4 = ledger_check.cursor()

    try:
        app_log.info("Verification of blocks started...")
        # verify blockchain
        h3.execute("SELECT * FROM misc order by block_height desc limit 1")
        db_rows = h3.fetchone()[0]
        app_log.info("Number of blocks: {}".format(db_rows))

        db_hashes = {
            8242: '4058bfeaca8280efcc19860b74ba4d1bd5c9eec4db468be5d14cb593',
            9487: 'adaa3745034811028023456eeb374ea0204c7d9a142815be2ba7fc1d',
            9786: '3cb4076ecde20c056675a75679aa8027d931ffd38b8d318c4013e660',
            27258: 'c338d39b7d675e90db63c000e5dda6d3ecc5b3d1b38697dcf18c1725',
            27298: 'c48e736aebdafe8483e1fff1bfd4771f1cdd387d4af51e5d6026e61c',
            30440: '930c192d2959abc80428fa8b4f90a37661eb1d7c239dc4eaebfb7618',
            32127: '2937783fb5b94b8381e4e5739b185222ad42b065b71a97cf295bc012',
            32128: '9af754f33710644a2fb5a39737df74e45b17fa4f599abf7ebcdafe77',
            37732: 'f8d6c049ed125b2c3cdf23fce024819f3066a7e0b77d542b32f35660',
            37898: 'e436fcfb9c7eea5fcc99d352bcaf7091bf07494bbcee545025aac23d',
            38083: '16af4205a2013739d3e4b9041d6fd58f1d289b2f90432e79271377d6',
            52233: 'a34499741b13e18408f6203d57ea0c6142453a4f28752e3542365990',
            52239: '7fad9c7ed488ee335337b1347de7545241dc18c9ebb315cedd72b72f',
            52282: '888ace79c603a425193d5fa79ac3ad587061e9fe864248e2fc4985cf',
            52308: '2c086d02ef5ceb92f18c1a0f539940d3c454927970867c551933d190',
            52393: '714aa366139b9228a08fbf5605aa0863df883faaa5983b156e8378ad',
            62507: '14c58afda4d3eb3046668074841a22456d370034efbd4b6e6ed8ace9',
            70094: 'ca44701770895bd1ba8c2ae9fa131bb8ad8fb9d641fe1d0abb91c219',
            116646: '1a630146349af911ce0348ed4d8d9ec5c47102377bcd92f4f9adcd2d',
            117298: 'ee62adac24a3d42c4529645f070d15375810c2b0759fc1c9cd1ad62a',
            126299: 'e2f91778fc41a72df269dba0be7a442149f6348d55863e7f7630818c',
            126971: '3f6485e663e9895d98ca3f8319031ea4765dd4592a3da87d67c6bec2',
            126981: '99030aec5a118b77620e137a2dc124ebc3daddc720143f74eb35727d',
            127085: 'a852d76ad0125e71d6ef8ad552784c634b666937e1516c84d591d97e',
            129904: '56c17469ffb83e83242b477058611d35fc8d850b8c43c131ad53e427',
            129905: '963db019944acfb382be98d7506fa35ae93a6a0b86417c844eafbbaa',
            130090: '4d3f9030d75243fc0ad4caa9eb91b56b46a369a83c85499b5ef0e3e3',
            204434: '60be79e6fe9d97ee2089747cf87790c111625c6e2d32c3a6b3e61d09',
            204453: 'f00b3c68b9fae7029f8ecf5cf16ffd7520e530bb0ceeeda6bfaa8953',
            204456: '6e5659ae26742db5f8cc2fd51be099b61efcbb508c246b689c653148',
            204503: '85aa4ee01a8ba849ee234a01b433ab40c1aeae52217eda577e683503',
            204505: '5973c2d89210d29c38a01017a9255bb20c5ac526a7ada7f2739740ff',
            204522: 'f17b834d272afbd49d0589c61c47cb712cc70192865d3f0b7167fc48',
            204581: '46d79cd8a87ee6055792f1ed9a831cca8e91588255dde5f858e45732',
            204649: '2facf1f742149e6633b1f30602fbec535c1000ef516b8e0df5e26f10',
            204718: '1857df85b145acdf8b9344673ce21cc1100443371ef76751aa700192',
            204790: '1b8ac8bc34d4b99d2339a99162411301f3066f45221ed033500036e0',
            204860: '902ac47ae4f119bad7ffb66dfedd8bc435f1e63380f9c78c8bf4a5df',
            204932: '25ebbd957028e05ef274498786ac7ad8ed5d11b33db817af16d1aa7d',
            204999: '12fbcdfd7f72e4867e863ee1cd9013318246e9ea6ca6fa86e2bf1087',
            205066: '1bf339b14ce8ec03ca3de0c08bd402975f65dccdc2474a2b11b63155',
            205140: '1772a0c86920f257317d026a7378184a54f69e2816eb3e259e3f4295',
            205157: 'c03529be3fc547c1ce08b366ee7efdd5091ce66a9b165a0a9b6eec94',
            205205: 'eccc43513099ed05d0aac389a6ce1aeeb4188527da7d73e4a14db37e',
            205274: '39b093a82b5d27639b917bf372fe7c99be59cb978fb4f3475e36c86a',
            205275: '5fbb2c73f5e91bfb0bb8a608ec23f94643d897cd7d648fe49b46e2c5',
            205344: 'd1085595cace93843212afc1adadb847bf25b2bea93f7ef177370ef2',
            205415: 'e06f50ab329406ed087e412d100da41b3bf58cb770f20cd6168de4d6',
            205487: '88ee8ad19e39ae30f7e1a0c5602da0bc6755575c25d2c43fc2fb9330',
            205503: '6eefdcb8e58b8a7bbc2e613caaf44a1a6e23d8a9e684981e015aaaaf',
            205556: 'c0961a54a1370c66a084ade2f00def65b8f89cfb21e793b7ae5c5b7c',
            205629: '99d15ac4b631286a0fee858890c26ad14dad5417603f436e38531344',
            205633: '3ec7fb7d18d3fe5c31d5510d08624d6fd4a4da0b5f6f991bc29c8370',
            205704: '745a7233e326553c1bb4d6cc49f7f8476d17b836456adb28490d523a'
        }

        print_step = 10000
        invalid = 0
        db_block_hash_prev = ""
        for row in h3.execute('SELECT * FROM transactions WHERE reward != 0 ORDER BY block_height'):
            db_block_height = row[0]
            db_block_hash = str(row[7])
            if db_block_height > 1:
                transaction_list_converted = []
                for transaction in h4.execute('SELECT * FROM transactions WHERE block_height={}'
                                              .format(db_block_height)):
                    q_received_timestamp = quantize_two(transaction[1])
                    received_timestamp = '%.2f' % q_received_timestamp
                    received_address = str(transaction[2])[:56]
                    received_recipient = str(transaction[3])[:56]
                    received_amount = '%.8f' % (quantize_eight(transaction[4]))
                    received_signature_enc = str(transaction[5])[:684]
                    received_public_key_hashed = str(transaction[6])[:1068]
                    received_operation = str(transaction[10])
                    received_openfield = str(transaction[11])

                    transaction_list_converted.append((received_timestamp, received_address, received_recipient,
                                                      received_amount, received_signature_enc,
                                                      received_public_key_hashed, received_operation,
                                                      received_openfield))

                block_hash = hashlib.sha224((str(transaction_list_converted) + db_block_hash_prev).encode("utf-8"))\
                    .hexdigest()
                if block_hash != db_block_hash:
                    try:
                        if block_hash != db_hashes[db_block_height]:
                            app_log.warning("Block hash mismatch: {}".format(db_block_height))
                            invalid = invalid + 1
                    except Exception as e:
                        app_log.warning("Block hash mismatch: {} {}".format(db_block_height, e))
                        invalid = invalid + 1

            db_block_hash_prev = db_block_hash

            if db_block_height > print_step:
                app_log.info("Bismuth blocks verified = {}".format(print_step))
                print_step += 10000

        if invalid == 0:
            app_log.info("All blocks in the local ledger are valid")
        else:
            app_log.warning("{} invalid blocks found".format(invalid))

        h3.close()
        h4.close()

    except Exception as e:
        app_log.info("Error: {}".format(e))
        raise

    return invalid


def check_block(block_height_new, miner_address, nonce, db_block_hash, diff0,
                received_timestamp, q_received_timestamp, q_db_timestamp_last):
    if block_height_new == POW_FORK - 1:
        diff0 = FORK_DIFF
    if block_height_new == POW_FORK:
        diff0 = FORK_DIFF

    bok = False
    real_diff = diffme_heavy3(miner_address, nonce, db_block_hash)
    diff_drop_time = Decimal(180)
    if real_diff >= int(diff0):
        bok = True

    elif Decimal(received_timestamp) > q_db_timestamp_last + Decimal(diff_drop_time):
        # uses block timestamp, don't merge with diff() for security reasons
        time_difference = q_received_timestamp - q_db_timestamp_last
        diff_dropped = quantize_ten(diff0) + quantize_ten(1) - quantize_ten(time_difference / diff_drop_time)
        # Emergency diff drop
        if Decimal(received_timestamp) > q_db_timestamp_last + Decimal(2 * diff_drop_time):
            factor = 10
            diff_dropped = quantize_ten(diff0) - quantize_ten(1) - \
                quantize_ten(factor * (time_difference - 2 * diff_drop_time) / diff_drop_time)

        if diff_dropped < 50:
            diff_dropped = 50
        if real_diff >= int(diff_dropped):
            bok = True

    return bok


def verify_diff(app_log, db):
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()
        h4 = ledger_check.cursor()

    try:
        app_log.info("Verification of diffs started...")
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

            if len(db_block_hash_prev) > 1:
                bok = check_block(db_block_height, miner_address, db_nonce, db_block_hash_prev, db_diff, db_timestamp,
                                  db_timestamp, db_timestamp_prev)

                if not bok:
                    app_log.warning("Diff mismatch: {}".format(db_block_height))
                    invalid = invalid + 1

            if db_block_height > print_step:
                app_log.info("Bismuth diffs verified = {}".format(print_step))
                print_step += 10000

            db_block_hash_prev = db_block_hash
            db_timestamp_prev = db_timestamp

        if invalid == 0:
            app_log.info("All diffs in the local ledger are valid")
        else:
            app_log.warning("{} invalid diffs found".format(invalid))

        h3.close()
        h4.close()

    except Exception as e:
        app_log.info("Error: {}".format(e))
        raise

    return invalid


def verify_rewards(app_log, db):
    with sqlite3.connect(db) as ledger_check:
        ledger_check.text_factory = str
        h3 = ledger_check.cursor()

    dev_acc = "4edadac9093d9326ee4b17f869b14f1a2534f96f9c5d7b48dc9acaed"
    hn_acc = "3e08b5538a4509d9daa99e01ca5912cda3e98a7f79ca01248c2bde16"
    rew_fork = 800000

    try:
        app_log.info("Verification of rewards started...")
        print_step = 50000
        invalid = 0

        for row in h3.execute('SELECT * FROM transactions where block_height<0 ORDER BY block_height DESC'):
            db_block_height = row[0]
            db_recipient = row[3]
            db_amount = row[4]

            if db_block_height > - rew_fork:
                rew_calc = 15 + db_block_height/1e6
                recipient = dev_acc
            elif db_block_height >= - HF2:
                if db_recipient == dev_acc:
                    rew_calc = 15 - 0.8 + db_block_height/5e5
                    recipient = dev_acc
                else:
                    rew_calc = 8.0
                    recipient = hn_acc
            elif db_block_height > - HF3:
                if db_recipient == dev_acc:
                    rew_calc = 15 - 2.4 + db_block_height/5e5
                    recipient = dev_acc
                else:
                    rew_calc = 24.0
                    recipient = hn_acc
            else:
                if db_recipient == dev_acc:
                    rew_calc = 9.7
                    if db_block_height < -HF3:
                        rew_calc = 5.5 + (HF3+db_block_height)/1.1e6
                    recipient = dev_acc
                else:
                    rew_calc = 10.0*(2.4 + (HF3+db_block_height-5)/3.0e6)
                    recipient = hn_acc

            rew_difference = quantize_eight(db_amount - rew_calc)
            if (rew_difference != 0) or (db_recipient != recipient):
                app_log.warning("Reward mismatch: {} {} {} {}".format(db_block_height,rew_difference,db_amount,rew_calc))
                invalid = invalid + 1

            if -db_block_height > print_step:
                app_log.info("Bismuth rewards verified = {}".format(print_step))
                print_step += 50000

        h3.close()

    except Exception as e:
        app_log.error("Error: {}".format(e))
        raise

    return invalid


if __name__ == "__main__":
    my_log = log.log("verify.log", "INFO", True)

    invalid1 = verify_txs(my_log, 'static/ledger.db', True)
    invalid2 = verify_blocks(my_log, 'static/ledger.db')
    invalid3 = verify_diff(my_log, 'static/ledger.db')
    invalid4 = verify_rewards(my_log, 'static/ledger.db')

    with open('snapshot.json') as json_data:
        config = json.load(json_data)

    with open("{}/ledger.json".format(config['DB_PATH'])) as json_data:
        data = json.load(json_data)

    if invalid1 + invalid2 + invalid3 + invalid4 == 0:
        data['valid'] = 'valid'
    else:
        data['valid'] = 'invalid'

    with open(config['DB_PATH'] + 'ledger.json', 'w') as outfile:
        json.dump(data, outfile)

