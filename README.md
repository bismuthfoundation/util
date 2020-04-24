# util
Small useful utility programs

* snapshot_create.py: Script which creates a vacuumed snapshot (backup) of the Bismuth blockchain. Requires only a short stop of node.py  
* ledger_verify.py:   Script which verifies Bismuth ledger: tx sigs, block hashes, diffs and rewards  
* snapshot_upload.py: Script which demonstrates AWS upload of ledger snapshot.  
* snapshot_download.py: Script to download and verify a snapshot.  
* wallet_json2der.py: To convert wallets from the Tornado wallet to legacy format  

These scripts can be combined in cronjobs, see instructions at top of snapshot_create.py

* privkey_to_wallet.py: Small utility to create a wallet file (new format) from address and privkey (old format). Pubkey found from ledger.
* hypernode_monitoring directory: Script for monitoring Bismuth hypernodes, creates 3 json files

Modules:
bismuthsimpleasset.py: Module for handling on-chain assets with myapp:register, myapp:unregister and asset id.  
