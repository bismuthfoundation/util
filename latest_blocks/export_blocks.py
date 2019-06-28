"""
Module for bloc exports
"""

import json
import sqlite3


KEYS = ("height", "hash", "timestamp", "mn_reward")


def hn_reward_for(block_height: int) -> int:
    if block_height % 10 == 0:
        return 24
    return 0


def print_latest_blocks(
    how_many: int = 100, db_dir: str = "/root/Bismuth/static/"
) -> None:
    print("{}ledger.db".format(db_dir))
    db = sqlite3.connect("{}ledger.db".format(db_dir))
    res = db.execute(
        "SELECT block_height, block_hash, CAST(timestamp as INT) "
        "from transactions WHERE reward > 0 "
        "ORDER BY block_height desc LIMIT ?",
        (how_many,),
    )
    blocks = res.fetchall()[::-1]  # list of tuples
    blocks = [dict(zip(KEYS, list(block) + [hn_reward_for(block[0])])) for block in blocks]
    print(json.dumps(blocks, indent=2))


if __name__ == "__main__":
    print("I'm a module, don't run me.")
