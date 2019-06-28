"""
Prints latest
"""

import config
from export_blocks import print_latest_blocks

if __name__ == "__main__":
    print_latest_blocks(100, config.BIS_STATIC_PATH)
