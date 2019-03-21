"""
Run this script in the main ~/Bismuth folder
The script creates a wallet file from address and privkey (old format)
"""

import os
import json
import base64
import sqlite3
import hashlib
from Cryptodome.PublicKey import RSA

def keys_save(private_key_readable, public_key_readable, address, file):
    wallet_dict = {}
    wallet_dict['Private Key'] = private_key_readable
    wallet_dict['Public Key'] = public_key_readable
    wallet_dict['Address'] = address

    if not isinstance(file,str):
        file = file.name

    with open (file, 'w') as keyfile:
        json.dump (wallet_dict, keyfile)


if __name__ == "__main__":
    print("----> This utility creates a Bismuth wallet file from a privkey (old format) and address")
    address = input("Enter the address: ")
    print("----> Searching ledger for pubkey")

    db = "static/ledger.db"
    with sqlite3.connect(db) as ledger:
        ledger.text_factory = str
    h = ledger.cursor()

    h.execute("SELECT public_key FROM transactions WHERE address = '{}' limit 1".format(address))
    result = h.fetchall()[0]
    public_key = str(result[0])
    public_key_readable = base64.b64decode(public_key).decode("utf-8")
    address_check = hashlib.sha224(public_key_readable.encode('utf-8')).hexdigest()

    if address == address_check:
        print("----> The specified address matches the public key found in ledger")
        privkey_file = input("Enter the name of file containing the privkey: ")
        key = RSA.importKey(open(privkey_file).read())
        private_key_readable = key.exportKey ().decode ("utf-8")
        wallet_file = input("Enter name of the new wallet file: ")

        if os.access(wallet_file, os.R_OK):
            print("----> This wallet file already exists. Utility aborted.")
        else:
            keys_save(private_key_readable, public_key_readable, address, wallet_file)
            print("----> File {} created.".format(wallet_file))

    else:
        print("----> The public key for the specified address is not found in the ledger")
