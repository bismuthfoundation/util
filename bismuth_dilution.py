"""
Script for calculating yearly dilution
of the Bismuth cryptocurrency
See also: https://hypernodes.bismuth.live/?p=218 
https://medium.com/@bismuthplatform/upcoming-bismuth-soft-fork-at-block-4-380-000-b50e4259ccfe
"""

def calc_rewards():
    rewards = []
    HF1 = 800000  # Block height at hard fork 1
    HF2 = 1200000 # Block height at hard fork 2
    HF3 = 1450000 # Block height at hard fork 3
    HF4 = 4380000 # block height at soft fork

    for block in range(1440*365*100):
        # determine pow_reward & pos_reward
        if block < HF1:
            pow_reward = 15.0 - block/1e6
            pos_reward = 0.0

        elif block < HF2:
            pow_reward = 15.0 - block/(1e6/2) - 0.8
            pos_reward = 0.8

        elif block < HF3:
            pow_reward = (11.8-1.6) - (block-HF2)/(0.5e6)
            pos_reward = 2.4

        else:
            pow_reward = 5.5 - (block-HF3)/(1.1e6)
            pos_reward  = 2.4 - (block-HF3)/(3.0e6)
            # enforce long-term minimum rewards
            pow_reward = max(pow_reward, 0.5)
            pos_reward = max(pos_reward, 0.5)

        # base dev cut for *all* blocks < HF4
        dev_reward = 0.1 * pow_reward

        # override at HF4: drop PoS & dev entirely
        if block >= HF4:
            pos_reward = 0.0
            dev_reward = 0.0

        rewards.append(pow_reward + pos_reward + dev_reward)

    return rewards

if __name__ == '__main__':
    rewards = calc_rewards()
    rewards_sum = sum(rewards[0:1440*365])
    for year in range(2,100):
        rewards_year = sum(rewards[(year-1)*1440*365:year*1440*365])
        print("Year {}: Dilution {}%".format(year,100*(rewards_year / rewards_sum)))
        rewards_sum = rewards_sum + rewards_year
