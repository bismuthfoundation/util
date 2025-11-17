#!/usr/bin/env python3
"""
Plot Bismuth mining reward and total supply up to year 2050,
using the *real* emission model (HF1–HF4 as in snapshot_create).

- HF1: 800,000     (first hard fork)
- HF2: 1,200,000   (second hard fork)
- HF3: 1,450,000   (BGV emission change)
- HF4: 4,380,000   (soft fork: remove dev & PoS rewards)

Assumptions:
- Genesis block date: 2017-05-01 (UTC)
- Block time: 60 seconds
- Total supply = miner + hypernode (PoS) + dev rewards
"""

from decimal import Decimal, getcontext
import datetime as dt
import matplotlib.pyplot as plt

# -------------------------------------------------------------------
# Emission parameters (real rules, matching snapshot_create.py logic)
# -------------------------------------------------------------------

getcontext().prec = 28  # plenty for our use

HF1 = 800_000
HF2 = 1_200_000
HF3 = 1_450_000
HF4 = 4_380_000

BLOCK_TIME_SECONDS = 60
GENESIS_DATETIME = dt.datetime(2017, 5, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
END_DATETIME = dt.datetime(2050, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)


def compute_rewards(height: int):
    """
    Return (miner_reward, hn_reward, dev_reward) as Decimals
    for a given block height, using the real fork logic.

    Matches the reward logic found in snapshot_create.py
    (minus quantize_eight rounding, which is negligible here).
    """
    h = Decimal(height)

    # Phase 1: pre-HF1
    if height < HF1:
        # 15 - height / 1_000_000
        miner = Decimal("15.0") - h / Decimal("1000000")
        hn = Decimal("0")

    # Phase 2: HF1 .. HF2 (inclusive)
    elif height <= HF2:
        # 15 - height / (1_000_000 / 2) - 0.8 ; HN = 0.8
        miner = (
            Decimal("15.0")
            - h / (Decimal("1000000") / Decimal("2"))
            - Decimal("0.8")
        )
        hn = Decimal("0.8")

    # Phase 3: HF2 .. HF3-1
    elif height < HF3:
        # (11.8 - 1.6) - (height - HF2) / 500_000 ; HN = 2.4
        miner = (
            Decimal("11.8")
            - Decimal("1.6")
            - (h - Decimal(HF2)) / Decimal("500000")
        )
        hn = Decimal("2.4")

    # Phase 4: HF3+ (BGV-style linear decay with floors)
    else:
        # Miner: 5.5 - (height - HF3) / 1.1e6, floor 0.5
        miner = Decimal("5.5") - (h - Decimal(HF3)) / Decimal("1100000")

        # HN: 2.4 - (height - HF3 + 5) / 3e6, floor 0.5
        hn = (
            Decimal("2.4")
            - (h - Decimal(HF3) + Decimal("5")) / Decimal("3000000")
        )

        if miner < Decimal("0.5"):
            miner = Decimal("0.5")
        if hn < Decimal("0.5"):
            hn = Decimal("0.5")

    # Dev reward: 10% of miner, but dropped at HF4
    if height >= HF4:
        hn = Decimal("0")        # no more Hypernode rewards
        dev = Decimal("0")       # no more dev rewards
    else:
        dev = miner * Decimal("0.10")

    return miner, hn, dev


def simulate_until_2050():
    """
    Simulate Bismuth emission from genesis until END_DATETIME.
    Returns:
        years         : list[int]
        supplies_mill : list[float]  (total supply in millions BIS)
        miner_rewards : list[float]  (mining reward per block)
    """
    # cumulative supplies
    cum_miner = Decimal("0")
    cum_hn = Decimal("0")
    cum_dev = Decimal("0")

    years = []
    supplies_millions = []
    miner_rewards = []

    # iterate block-by-block until end of 2050
    height = 1
    current_time = GENESIS_DATETIME + dt.timedelta(seconds=BLOCK_TIME_SECONDS)
    dt_block = dt.timedelta(seconds=BLOCK_TIME_SECONDS)

    last_recorded_year = None

    while current_time <= END_DATETIME:
        miner, hn, dev = compute_rewards(height)

        cum_miner += miner
        cum_hn += hn
        cum_dev += dev

        total_supply = cum_miner + cum_hn + cum_dev

        year = current_time.year
        if last_recorded_year is None or year > last_recorded_year:
            # First block we encounter in this year: record snapshot
            years.append(year)
            supplies_millions.append(float(total_supply / Decimal("1e6")))
            miner_rewards.append(float(miner))
            last_recorded_year = year

        height += 1
        current_time += dt_block

    return years, supplies_millions, miner_rewards


def plot_bismuth_supply_and_reward():
    years, supplies_millions, miner_rewards = simulate_until_2050()

    plt.style.use("dark_background")

    fig, ax1 = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("#1e1e1e")
    ax1.set_facecolor("#1e1e1e")

    ax2 = ax1.twinx()
    ax2.set_facecolor("#1e1e1e")

    # Left axis: total BIS supply (millions)
    ax1.plot(
        years,
        supplies_millions,
        color="#9be564",
        linewidth=2.5,
        marker="o",
        label="BIS Supply",
    )
    ax1.set_xlabel("Year")
    ax1.set_ylabel("BIS Supply (millions)", color="#9be564")
    ax1.tick_params(axis="y", labelcolor="#9be564")

    # Nice x ticks: every 2–5 years depending on span
    if len(years) > 2:
        step = 5
        xticks = list(range(years[0], years[-1] + 1, step))
        ax1.set_xticks(xticks)

    # Right axis: PoW mining reward per block
    ax2 = ax1.twinx()
    ax2.step(
        years,
        miner_rewards,
        where="post",
        color="#ff7f7f",
        linewidth=2.0,
        label="BIS Mining Reward / Block",
    )
    # --- Tail emission annotation ---
    TAIL_HEIGHT = 6_950_000  # first block where reward hits 0.5 BIS
    years_list = years       # already in your script
    miner_list = miner_rewards

    # Find the nearest year index (first year >= TAIL_HEIGHT)
    blocks_per_year = int((365*24*3600) / 60)   # ~525,600 blocks each year at 60s blocktime
    tail_year = int(2017 + TAIL_HEIGHT / blocks_per_year)

    # Draw a vertical dotted line
    ax1.axvline(tail_year, color="#888888", linestyle="--", linewidth=1)

    # Add label
    ax1.text(
        tail_year + 0.3,
        max(supplies_millions) * 0.85,
        "0.5 BIS tail emission begins",
        color="#cccccc",
        fontsize=9
    )

    # Also annotate the reward curve at this point
    ax2.annotate(
        "0.5 BIS",
        xy=(tail_year, 0.5),
        xytext=(tail_year + 1.5, 1.0),
        color="#ffaaaa",
        arrowprops=dict(arrowstyle="->", color="#ffaaaa"),
        fontsize=9
    )

    ax2.set_ylabel("Mining Reward (BIS per block)", color="#ff7f7f")
    ax2.tick_params(axis="y", labelcolor="#ff7f7f")

    # Title & grid
    fig.suptitle(
        "Bismuth Mining Reward and Supply over the Years",
        fontsize=14,
    )
    ax1.grid(alpha=0.2)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_bismuth_supply_and_reward()
