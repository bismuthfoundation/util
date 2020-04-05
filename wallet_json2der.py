"""
Script for generating a legacy wallet.der from an encrypted Tornado wallet.json
"""

import json
import getpass
from bismuthclient.bismuthmultiwallet import BismuthMultiWallet

w = BismuthMultiWallet()

w.load()
info = w.info()
N = info['count']
print("The multiwallet contains {} addresses:".format(N))

address = input('Address you want to export: ')
password = getpass.getpass('Enter wallet master password:')
w.unlock(password)
w.set_address(address)

wallet = {}
wallet['Private Key'] = repr(w.key.exportKey().decode('unicode_escape')).replace("'","")
wallet['Public Key'] = repr(w.public_key).encode().decode('unicode_escape').replace("'","")
wallet['Address'] = address
print(json.dumps(wallet))
