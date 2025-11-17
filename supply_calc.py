import os
import matplotlib.pyplot as plt
import urllib3
import json
import time
import datetime
from decimal import Decimal, getcontext

# ----------------------------
# Precision and helpers
# ----------------------------

getcontext().prec = 28  # plenty for our needs


def quantize_eight(value) -> Decimal:
    """Quantize to 8 decimal places, like the node does."""
    return Decimal(value).quantize(Decimal("0.00000001"))


# ----------------------------
# Network & fork configuration
# ----------------------------

HF1 = 800_000      # Hypernodes launch
HF2 = 1_200_000    # Strategic hard fork v4.3.0.0
HF3 = 1_450_000    # BGV-01 emission change
SOFT_FORK = 4_380_000  # 2025 soft fork: remove dev + hypernode rewards

BLOCKTIME = 60          # seconds
MAX_BLOCKS = 50_000_000
MILESTONE_BLOCK_X = [10, 20, 30, 40, 50]  # in millions (x-axis positions)


def get_network_height():
    """
    Returns (network_height, last_block_time_str_or_ts) from bismuth.im API.
    Returns (False, False) if the API is not available.
    """
    http = urllib3.PoolManager()
    try:
        chainjson = http.request('GET', 'https://bismuth.im/api/node/blocklast')
        chain = json.loads(chainjson.data.decode('utf-8'))
        height = int(chain["block_height"])
        last_block_time = chain["timestamp"]  # e.g. "2025/07/18,06:06:59" or UNIX
        print("Bismuth.im API says network height is {}".format(height))
        return height, last_block_time
    except Exception as e:
        print("bismuth.im API not reachable, no actual values shown ({})".format(e))
        return False, False


# ----------------------------
# Emission model (piecewise, Decimal-based)
# ----------------------------

def block_rewards(height: int):
    """
    Return per-block rewards for a given height:

        (miner_reward, dev_reward, pos_reward)

    Using Decimal + quantize_eight() to mirror node behaviour
    and snapshot_create.py logic as closely as possible.
    """
    h = Decimal(height)

    # Phase 1: genesis -> HF1
    if height < HF1:
        miner = Decimal("15") - h / Decimal("1000000")
        hn = Decimal("0")

    # Phase 2: HF1 .. HF2 (inclusive)
    elif height <= HF2:
        miner = (
            Decimal("15")
            - h / (Decimal("1000000") / Decimal("2"))
            - Decimal("0.8")
        )
        hn = Decimal("0.8")

    # Phase 3: HF2 .. HF3-1
    elif height < HF3:
        miner = (
            Decimal("11.8")
            - Decimal("1.6")
            - (h - Decimal(HF2)) / Decimal("500000")
        )
        hn = Decimal("2.4")

    # Phase 4: HF3+ (BGV linear decay with floors)
    else:
        # Miner: 5.5 - (height - HF3)/1.1e6, floor 0.5
        miner = Decimal("5.5") - (h - Decimal(HF3)) / Decimal("1100000")
        if miner < Decimal("0.5"):
            miner = Decimal("0.5")

        # HN: 2.4 - (height - HF3 + 5)/3e6, floor 0.5
        hn = (
            Decimal("2.4")
            - (h - Decimal(HF3) + Decimal("5")) / Decimal("3000000")
        )
        if hn < Decimal("0.5"):
            hn = Decimal("0.5")

    miner = quantize_eight(miner)
    hn = quantize_eight(hn)

    # Dev rewards: 10% of miner – until soft fork removes dev + HN
    dev = quantize_eight(miner * Decimal("0.10"))

    # Apply soft fork: remove dev and hypernode rewards from 4,380,000 onward
    if height >= SOFT_FORK:
        dev = Decimal("0")
        hn = Decimal("0")

    return miner, dev, hn


# ----------------------------
# Simulation & plotting
# ----------------------------

# initialise arrays for plotting (floats for matplotlib)
block = [0.0]
supply = [0.0]
rewards_miners = [0.0]
rewards_dev = [0.0]
rewards_pos = [0.0]
reward_block_mining = [15.0]
reward_block_dev = [15.0 * 0.10]
reward_block_pos = [0.0]
convert_to_date = []

# cumulative supplies (Decimal)
cum_miner = Decimal("0")
cum_dev = Decimal("0")
cum_pos = Decimal("0")

# debug: cumulative at network height
actual_miner_cum = Decimal("0")
actual_dev_cum = Decimal("0")
actual_pos_cum = Decimal("0")

j = 1  # plotting step counter
PLOT_STEP = 50_000  # every 50k blocks

# Try to get network height from API
network_height, last_block_mined = get_network_height()

# These will be filled when we pass network_height
actual_supply = Decimal("0")
actual_mining_reward = Decimal("0")
reward_zero_height = None

for i in range(1, MAX_BLOCKS + 1):
    miner_r, dev_r, pos_r = block_rewards(i)

    # Track when miner reward hits exactly 0 (legacy; not used with current floor)
    if miner_r <= Decimal("0") and reward_zero_height is None:
        reward_zero_height = i

    cum_miner += miner_r
    cum_dev += dev_r
    cum_pos += pos_r

    # Sample points for plotting every 50k blocks
    if i == j * PLOT_STEP:
        block.append(i / 1_000_000.0)
        total_supply = (cum_miner + cum_dev + cum_pos) / Decimal("1000000")
        supply.append(float(total_supply))

        rewards_miners.append(float(cum_miner / Decimal("1000000")))
        rewards_dev.append(float(cum_dev / Decimal("1000000")))
        rewards_pos.append(float(cum_pos / Decimal("1000000")))

        reward_block_mining.append(float(miner_r))
        reward_block_dev.append(float(dev_r))
        reward_block_pos.append(float(pos_r))

        j += 1

    # Capture actual supply at current height
    if network_height and i == network_height:
        actual_supply = cum_miner + cum_dev + cum_pos
        actual_mining_reward = miner_r

        # debug breakdown at network height
        actual_miner_cum = cum_miner
        actual_dev_cum = cum_dev
        actual_pos_cum = cum_pos

# ---------------
# Debug: print emission breakdown at network height
# ---------------

if network_height and actual_supply > 0:
    print("\n--- DEBUG emission model at network height ---")
    print(f"Height from API      : {network_height}")
    print(f"Total supply (model) : {actual_supply:.8f} BIS")
    print(f"  Miner cumulative   : {actual_miner_cum:.8f} BIS")
    print(f"  Dev cumulative     : {actual_dev_cum:.8f} BIS")
    print(f"  HN/PoS cumulative  : {actual_pos_cum:.8f} BIS")
    print("  (sum miner+dev+pos): {:.8f} BIS\n".format(
        actual_miner_cum + actual_dev_cum + actual_pos_cum))

# ---------------
# Time estimates
# ---------------

milestone_x = []          # x-positions (in millions) for vertical lines
tail_label_index = None   # index of tail date in convert_to_date
current_x = None          # x position of current height
current_date_str = None   # readable date for current height

if last_block_mined and network_height:
    # last_block_mined can be a float (UNIX) or a "YYYY/MM/DD,HH:MM:SS" string
    if isinstance(last_block_mined, (float, int)):
        unixtime_last_block = float(last_block_mined)

        # Some nodes may return ms; normalize to seconds
        if unixtime_last_block > 1e12:
            unixtime_last_block /= 1000.0
    else:
        unixtime_last_block = time.mktime(
            datetime.datetime.strptime(last_block_mined, "%Y/%m/%d,%H:%M:%S").timetuple()
        )

    current_x = network_height / 1_000_000.0
    current_date_str = datetime.datetime.utcfromtimestamp(
        unixtime_last_block
    ).strftime('%Y/%m/%d')

    # Milestones at absolute heights: 10M, 20M, 30M, 40M, 50M
    for x in MILESTONE_BLOCK_X:
        target_height = int(x * 1_000_000)

        # only future milestones
        if target_height <= network_height:
            continue

        est_time_of_block = unixtime_last_block + (
            (target_height - network_height) * BLOCKTIME
        )
        convert_to_date.append(
            datetime.datetime.utcfromtimestamp(est_time_of_block)
            .strftime('%Y/%m/%d')
        )
        milestone_x.append(x)

    # estimated time when miner reward hits tail (6.95M)
    tail_height = 6_950_000
    if tail_height > network_height:
        est_time_tail = unixtime_last_block + ((tail_height - network_height) * BLOCKTIME)
        convert_to_date.append(
            datetime.datetime.utcfromtimestamp(est_time_tail)
            .strftime('%Y/%m/%d')
        )
        tail_label_index = len(convert_to_date) - 1


# ----------------------------
# First plot: total supply
# ----------------------------

if last_block_mined and network_height:
    os.makedirs("graphics", exist_ok=True)

    plt.figure()

    # milestone verticals (fixed at 10,20,30,40,50 where applicable)
    for x in milestone_x:
        plt.axvline(x=x, color='C0')

    # vertical line at current block height (light grey)
    if current_x is not None:
        plt.axvline(x=current_x, color='lightgrey', linestyle='--', linewidth=1)
        # date label for current height near the top (y=95)
        if current_date_str:
            plt.text(
                current_x,
                95,
                current_date_str,
                fontsize=8,
                ha='center',
                color='grey'
            )

    # milestone date labels at those x positions (future only)
    for idx, x in enumerate(milestone_x):
        if idx < len(convert_to_date):
            plt.text(x, 90, convert_to_date[idx], fontsize=8)

    # total supply curve
    plt.plot(
        block, supply,
        color='green', linestyle='solid', linewidth=2,
        marker='.', markersize=3, label='total supply (model)'
    )

    # actual on-chain point (model point at current height)
    if actual_supply > 0 and network_height:
        plt.plot(
            (network_height / 1_000_000.0),
            (float(actual_supply) / 1_000_000.0),
            color='red', linestyle='solid', linewidth=0,
            marker='o', markersize=5, label='actual height (model)'
        )
        plt.annotate(
            int(actual_supply),
            xy=((network_height / 1_000_000.0), (float(actual_supply) / 1_000_000.0)),
            xytext=((network_height / 1_000_000.0) + 3, (float(actual_supply) / 1_000_000.0)),
            arrowprops=dict(facecolor='black', shrink=0.05),
        )

    # per-category cumulative supplies
    plt.plot(block, rewards_dev,
             color='blue', linestyle='solid', linewidth=2,
             marker='.', markersize=3, label='dev rewards (cum)')

    plt.plot(block, rewards_miners,
             color='purple', linestyle='solid', linewidth=2,
             marker='.', markersize=3, label='miners rewards (cum)')

    plt.plot(block, rewards_pos,
             color='brown', linestyle='solid', linewidth=2,
             marker='.', markersize=3, label='PoS / HN rewards (cum)')

    # axis limits
    plt.ylim(0, 100)
    plt.xlim(0, 50)

    # extra horizontal guide lines + light-grey tick labels at 35, 45, 50
    extra_ticks = [35, 45, 50]

    # merge extra ticks into current ticks
    yticks = list(plt.yticks()[0])
    new_ticks = sorted(set(yticks + extra_ticks))
    plt.yticks(new_ticks)

    ax = plt.gca()
    for label in ax.get_yticklabels():
        try:
            val = float(label.get_text())
        except ValueError:
            continue
        if val in extra_ticks:
            label.set_color('lightgrey')
            label.set_fontsize(8)

    for level in extra_ticks:
        plt.axhline(y=level, color='lightgrey', linestyle='--', linewidth=1)

    plt.xlabel('block * 1,000,000')
    plt.ylabel('BIS * 1,000,000')
    plt.legend(loc='upper left')
    plt.title('BIS supply over blocks and estimated milestone dates')
    plt.savefig('graphics/supply.png', dpi=600)
    plt.show()
else:
    print("Bismuth-API wasn't reachable, no plotting possible (supply plot)")

# ----------------------------
# Second plot: per-block rewards
# ----------------------------

if last_block_mined and network_height and actual_mining_reward:
    plt.figure()

    # milestone verticals (same x as above)
    for x in milestone_x:
        plt.axvline(x=x, color='C0')

    # vertical line at current block height (light grey)
    if current_x is not None:
        plt.axvline(x=current_x, color='lightgrey', linestyle='--', linewidth=1)

        # date label for current block at the top (a bit higher)
        if current_date_str:
            plt.text(
                current_x,
                15.2,          # moved up
                current_date_str,
                fontsize=8,
                ha='center',
                color='grey'
            )

        # block height label further below x-axis
        plt.text(
            current_x,
            -0.8,           # moved down
            f"{network_height:,}",
            ha='center',
            fontsize=8,
            color='grey'
        )

    # ------------------------------------------------------
    # Tail emission date line and label (0.5 BIS floor)
    # ------------------------------------------------------
    tail_height = 6_950_000
    tail_x = tail_height / 1_000_000.0

    if tail_label_index is not None and last_block_mined and network_height:
        tail_date = convert_to_date[tail_label_index]

        # thin vertical line for tail event
        plt.axvline(x=tail_x, color='lightgrey', linestyle=':', linewidth=1)

        # label above the line, slightly lower than current-date label
        plt.text(
            tail_x,
            14.2,          # slightly lower
            tail_date,
            fontsize=8,
            ha='center',
            color='grey'
        )

        # label below the line, slightly above current block height text
        plt.text(
            tail_x,
            -0.4,          # slightly above
            "0.5 BIS tail",
            fontsize=8,
            ha='center',
            color='grey'
        )

    # milestone dates a bit lower in y (for milestone lines only)
    for idx, x in enumerate(milestone_x):
        if idx < len(convert_to_date):
            plt.text(x, 14, convert_to_date[idx], fontsize=8)

    # dev, miner, pos block rewards
    plt.plot(block, reward_block_dev,
             color='blue', linestyle='solid', linewidth=2,
             marker='.', markersize=3, label='dev block reward')

    plt.plot(block, reward_block_mining,
             color='#0b8a22', linestyle='solid', linewidth=2,   # dark green
             marker='.', markersize=3, label='miners block reward')

    plt.plot(block, reward_block_pos,
             color='brown', linestyle='solid', linewidth=2,
             marker='.', markersize=3, label='PoS / HN block reward')

    # annotate where miner reward is at current height
    plt.annotate(
        float(round(actual_mining_reward, 3)),
        xy=((network_height / 1_000_000.0), float(actual_mining_reward)),
        xytext=((network_height / 1_000_000.0) + 1, float(actual_mining_reward) + 1),
        arrowprops=dict(facecolor='black', shrink=0.05),
    )

    if reward_zero_height:
        plt.annotate(
            reward_zero_height,
            xy=((reward_zero_height / 1_000_000.0), 0),
            xytext=((reward_zero_height / 1_000_000.0), 2),
            arrowprops=dict(facecolor='black', shrink=0.05),
        )

    plt.ylim(-0.5, 15)
    plt.xlim(0, 50)
    plt.xlabel('block * 1,000,000')
    plt.ylabel('BIS')
    plt.legend(loc='right')
    plt.title('BIS rewards per category and estimated milestone dates')
    plt.savefig('graphics/rewards.png', dpi=600)
    plt.show()
else:
    print("Bismuth-API wasn't reachable, no plotting possible (rewards plot)")
