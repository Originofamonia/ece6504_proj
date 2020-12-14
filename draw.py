import matplotlib.pyplot as plt


def draw_ppo():
    file1 = open('rewards/avg_rewards_ppo_c2_0.1.txt', 'r')
    lines = file1.readlines()
    ppo = list()
    for line in lines:
        ppo.append(float(line.strip()))

    file2 = open('rewards/avg_rewards_ppo_0.2.txt', 'r')
    lines = file2.readlines()
    ppo2 = list()
    for line in lines:
        ppo2.append(float(line.strip()))

    file3 = open('rewards/avg_rewards_ppo_c2_0.8.txt', 'r')
    lines = file3.readlines()
    ppo3 = list()
    for line in lines:
        ppo3.append(float(line.strip()))

    file4 = open('rewards/avg_rewards_ppo_c2_1.5.txt', 'r')
    lines = file4.readlines()
    ppo4 = list()
    for line in lines:
        ppo4.append(float(line.strip()))

    file5 = open('rewards/avg_rewards_ppo_c2_2.txt', 'r')
    lines = file5.readlines()
    ppo5 = list()
    for line in lines:
        ppo5.append(float(line.strip()))

    line1, = plt.plot(ppo)
    line2, = plt.plot(ppo2)
    line3, = plt.plot(ppo3)
    line4, = plt.plot(ppo4)
    line5, = plt.plot(ppo5)
    line1.set_label('1:0.1')
    line2.set_label('1:0.5')
    line3.set_label('1:0.8')
    line4.set_label('1:1.5')
    line5.set_label('1:2')
    plt.xlabel('Ratio of c1 and c2')
    plt.ylabel('Rewards')
    plt.legend()
    plt.show()


def main():
    file1 = open('rewards/avg_rewards_ppo.txt', 'r')
    lines = file1.readlines()
    ppo = list()
    for line in lines:
        ppo.append(float(line.strip()))

    file2 = open('rewards/avg_rewards_trpo.txt', 'r')
    lines = file2.readlines()
    trpo = list()
    for line in lines:
        trpo.append(float(line.strip()))

    line1, = plt.plot(ppo)
    line2, = plt.plot(trpo)
    line1.set_label('PPO')
    line2.set_label('TRPO')
    plt.xlabel('Episodes')
    plt.ylabel('Rewards')
    plt.legend()
    plt.show()


if __name__ == '__main__':
    # main()
    draw_ppo()
