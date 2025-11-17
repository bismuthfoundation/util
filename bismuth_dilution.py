#!/usr/bin/env python3
"""
Dilution calculator for Bismuth, aligned with chain emission rules:

- Genesis block: 2017-05-01 (no premine)
- HF1..HF3: historical Bismuth emission phases
- HF3 tail-decay with miner / HN floors at 0.5 BIS
- HF4 (block 4,380,000): removal of Dev + HN/PoS rewards
- Uses Decimal + quantize_eight() like the ledger
- Groups results by *calendar year* (2017, 2018, 2019, ...)
- Exports results to dilution.csv
"""

import csv
import datetime as dt
from decimal import Decimal, getcontext

# --------------------------------------------------------------------
# Precision & constants
# --------------------------------------------------------------------

getcontext().prec = 28  # high precision, as in chain code

# Fork heights (block heights)
HF1 = 800_000
HF2 = 1_200_000
HF3 = 1_450_000
HF4 = 4_380_000   # soft fork: remove dev + PoS rewards

# Time assumptions
BLOCK_TIME_SECONDS = 60
GENESIS_DATETIME = dt.datetime(2017, 5, 1, 0, 0, 0, tzinfo=dt.timezone.utc)

# How many calendar years to simulate (starting from 2017)
YEARS_TO_SIMULATE = 100
END_YEAR = GENESIS_DATETIME.year + YEARS_TO_SIMULATE - 1  # inclusive


def quantize_eight(value) -> Decimal:
    """Quantize to 8 decimal places, like the ledger."""
    return Decimal(value).quantize(Decimal("0.00000001"))


def per_block_rewards(height: int):
    """
    Return (pow_reward, pos_reward, dev_reward) as Decimals
    for a given block height, matching chain emission logic.
    """
    h = Decimal(height)

    # Phase 1: genesis -> HF1
    if height < HF1:
        pow_reward = Decimal("15.0") - h / Decimal("1000000")
        pos_reward = Decimal("0.0")

    # Phase 2: HF1 .. HF2 (inclusive)
    elif height <= HF2:
        pow_reward = (
            Decimal("15.0")
            - h / (Decimal("1000000") / Decimal("2"))
            - Decimal("0.8")
        )
        pos_reward = Decimal("0.8")

    # Phase 3: HF2 .. HF3-1
    elif height < HF3:
        pow_reward = (
            Decimal("11.8")
            - Decimal("1.6")
            - (h - Decimal(HF2)) / Decimal("500000")
        )
        pos_reward = Decimal("2.4")

    # Phase 4: HF3+ (BGV linear decay, floors at 0.5)
    else:
        # Miner: 5.5 → 0.5 over ~1.1M blocks
        pow_reward = Decimal("5.5") - (h - Decimal(HF3)) / Decimal("1100000")
        if pow_reward < Decimal("0.5"):
            pow_reward = Decimal("0.5")

        # HN/PoS: 2.4 → 0.5 over ~3M blocks, with +5 offset like the node
        pos_reward = (
            Decimal("2.4")
            - (h - Decimal(HF3) + Decimal("5")) / Decimal("3000000")
        )
        if pos_reward < Decimal("0.5"):
            pos_reward = Decimal("0.5")

    # Quantize miner & HN rewards
    pow_reward = quantize_eight(pow_reward)
    pos_reward = quantize_eight(pos_reward)

    # Dev reward: 10% of miner, until HF4
    dev_reward = quantize_eight(pow_reward * Decimal("0.10"))

    # After HF4: no PoS & no dev
    if height >= HF4:
        pos_reward = Decimal("0.0")
        dev_reward = Decimal("0.0")

    return pow_reward, pos_reward, dev_reward


def simulate_yearly_dilution():
    """
    Simulate block-by-block from genesis, grouping rewards by calendar year.

    Returns:
        List of dicts with keys:
        - year
        - new_bis
        - dilution_pct
        - cumulative_supply
    """
    results = []

    # State
    current_time = GENESIS_DATETIME
    current_year = current_time.year

    total_supply = Decimal("0")          # total supply up to current block
    supply_before_year = Decimal("0")    # supply at start of current_year
    year_new = Decimal("0")              # new coins minted in current_year

    height = 0

    # Run until we pass END_YEAR
    while current_time.year <= END_YEAR:
        height += 1

        # Calculate rewards for this block height
        pow_r, pos_r, dev_r = per_block_rewards(height)
        block_reward = quantize_eight(pow_r + pos_r + dev_r)

        # Update totals
        total_supply += block_reward
        year_new += block_reward

        # Advance time by one block
        current_time += dt.timedelta(seconds=BLOCK_TIME_SECONDS)
        new_year = current_time.year

        # Did we move to a new calendar year?
        if new_year != current_year:
            # Finalize the year we just completed: current_year
            if supply_before_year == 0:
                # For 2017 (partial first year from May 1st), dilution is undefined / 0
                dilution_pct = Decimal("0")
            else:
                dilution_pct = (year_new / supply_before_year) * Decimal("100")

            results.append({
                "year": current_year,
                "new_bis": year_new,
                "dilution_pct": dilution_pct,
                "cumulative_supply": total_supply,
            })

            # Prepare for next year
            current_year = new_year
            supply_before_year = total_supply
            year_new = Decimal("0")

            # Stop if we've passed END_YEAR
            if current_year > END_YEAR:
                break

    return results


if __name__ == "__main__":
    results = simulate_yearly_dilution()

    # -----------------------------
    # Write CSV
    # -----------------------------
    with open("dilution.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Year", "New BIS Issued", "Annual Dilution %", "Cumulative Supply"])

        for r in results:
            writer.writerow([
                r["year"],
                f"{r['new_bis']:.8f}",
                f"{r['dilution_pct']:.6f}",
                f"{r['cumulative_supply']:.8f}",
            ])

    # -----------------------------
    # Console output
    # -----------------------------
    for r in results:
        year = r["year"]
        new_bis = float(r["new_bis"])
        dil = float(r["dilution_pct"])
        cum = float(r["cumulative_supply"])

        print(
            f"Year {year}: "
            f"New {new_bis:.4f} BIS, "
            f"Dilution {dil:.6f}%, "
            f"Cumulative Supply {cum:.4f} BIS"
        )
