import os
import gym
import random
import argparse
import numpy as np

import torch
from model import Actor, Critic
from torch.distributions import Categorical

parser = argparse.ArgumentParser()
parser.add_argument('--env_name', type=str, default="CartPole-v1")
parser.add_argument("--load_model", type=str, default='model.pth')
parser.add_argument('--render', action="store_true", default=True)
parser.add_argument('--hidden_size', type=int, default=64)
parser.add_argument('--iter', type=int, default=10000)
parser.add_argument('--log_interval', type=int, default=10)
args = parser.parse_args()

def get_action(policies):
    m = Categorical(policies)
    action = m.sample()
    action = action.data.numpy()[0]
    return action

if __name__=="__main__":
    env = gym.make(args.env_name)
    env.seed(500)
    torch.manual_seed(500)

    state_size = env.observation_space.shape[0]
    action_size = env.action_space.n
    print('state size:', state_size)
    print('action size:', action_size)

    actor_net = Actor(state_size, action_size, args)
    critic_net = Critic(state_size, args)
    
    if args.load_model is not None:
        pretrained_model_path = os.path.join(os.getcwd(), 'save_model', str(args.load_model))
        pretrained_model = torch.load(pretrained_model_path)
        actor_net.load_state_dict(pretrained_model['actor'])
        critic_net.load_state_dict(pretrained_model['critic'])

    steps = 0
    
    for episode in range(args.iter):
        done = False
        score = 0

        state = env.reset()
        state = np.reshape(state, [1, state_size])

        while not done:
            if args.render:
                env.render()

            steps += 1
            policies = actor_net(torch.Tensor(state))
            action = get_action(policies)
            
            next_state, reward, done, _ = env.step(action)

            next_state = np.reshape(next_state, [1, state_size])            
            reward = reward if not done or score == 499 else -1

            state = next_state
            score += reward

        if episode % args.log_interval == 0:
            print('{} episode | score: {:.2f}'.format(episode, score))