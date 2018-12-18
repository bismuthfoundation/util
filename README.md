# util
Small useful utility programs

* snapshot_create.py: Script which creates a vacuumed snapshot (backup) of the Bismuth blockchain. Requires only a short stop of node.py  
* ledger_verify.py:   Script which verifies Bismuth ledger: tx sigs, block hashes, diffs and rewards  
* snapshot_upload.py: Script which demonstrates AWS upload of ledger snapshot.  

The three scripts above can be combined in one cronjob, see instructions at top of snapshot_create.py
