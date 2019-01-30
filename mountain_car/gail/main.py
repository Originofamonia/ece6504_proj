import os
import gym
import pylab
import argparse
import numpy as np

import torch
import torch.optim as optim
from tensorboardX import SummaryWriter 

from utils.memory import Memory
from utils.utils import get_action, get_reward
from model import Actor, Critic, Discriminator
from train_model import train_actor_critic, train_discrim

parser = argparse.ArgumentParser(description='PyTorch GAIL')
parser.add_argument('--env_name', type=str, default="MountainCar-v0", 
                    help='name of the environment to run')
parser.add_argument('--load_model', type=str, default=None, 
                    help='')
parser.add_argument('--load_demo_count', type=int, default=5000, 
                    help='count of demonstrations to load')
parser.add_argument('--save_path', type=str, default='./save_model/', 
                    help='path to save the model')
parser.add_argument('--render', action="store_true", default=False, 
                    help='if you dont want to render, set this to False')
parser.add_argument('--gamma', type=float, default=0.99, 
                    help='discounted factor')
parser.add_argument('--lamda', type=float, default=0.98, 
                    help='GAE hyper-parameter')
parser.add_argument('--hidden_size', type=int, default=50, 
                    help='hidden unit size of actor, critic and discrim networks')
parser.add_argument('--learning_rate', type=float, default=3e-4, 
                    help='learning rate of models')
parser.add_argument('--l2_rate', type=float, default=1e-3, 
                    help='l2 regularizer coefficient')
parser.add_argument('--clip_param', type=float, default=0.2, 
                    help='clipping parameter for PPO')
parser.add_argument('--total_sample_size', type=int, default=4096, 
                    help='total batch to collect before PPO update (default: 4096)')
parser.add_argument('--batch_size', type=int, default=128, 
                    help='batch size to update (default: 128)')
parser.add_argument('--seed', type=int, default=500,
                    help='random seed (default: 500)')
parser.add_argument('--logdir', type=str, default='logs',
                    help='tensorboardx logs directory')
args = parser.parse_args()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if args.load_demo_count == 5000:
    load_demo = './make_expert/expert_demo_5031.npy'
elif args.load_demo_count == 20000:
    load_demo = './make_expert/expert_demo_20011.npy'
elif args.load_demo_count == 35000:
    load_demo = './make_expert/expert_demo_35011.npy'
elif args.load_demo_count == 50000:
    load_demo = './make_expert/expert_demo_50116.npy'


def main():
    env = gym.make(args.env_name)
    env.seed(args.seed)
    torch.manual_seed(args.seed)

    num_inputs = env.observation_space.shape[0]
    num_actions = env.action_space.n
    action_dim = 1 if len(env.action_space.shape) == 0 else env.action_space.shape[0]

    print('state size:', num_inputs)
    print('action size:', num_actions)
    print('action_dim:', action_dim)

    actor = Actor(num_inputs, num_actions, args).to(device)
    critic = Critic(num_inputs, args).to(device)
    discrim = Discriminator(num_inputs + action_dim, args).to(device)

    actor_optim = optim.Adam(actor.parameters(), lr=args.learning_rate) 
    critic_optim = optim.Adam(critic.parameters(), lr=args.learning_rate, 
                              weight_decay=args.l2_rate) 
    discrim_optim = optim.Adam(discrim.parameters(), lr=args.learning_rate)
    
    demonstrations = np.load(load_demo)
    print("demonstrations.shape", demonstrations.shape)

    # writer = SummaryWriter(args.logdir)

    if not os.path.isdir(args.save_path):
        os.makedirs(args.save_path)

    if args.load_model is not None:
        saved_ckpt_path = os.path.join(os.getcwd(), 'save_model', str(args.load_model))
        ckpt = torch.load(saved_ckpt_path)

        actor.load_state_dict(ckpt['actor'])
        critic.load_state_dict(ckpt['critic'])
        discrim.load_state_dict(ckpt['discrim'])

    episodes, scores = [], []
    episode = 0    

    for iter in range(1000):
        actor.eval(), critic.eval()
        memory = Memory()
        
        step = 0

        while step < args.total_sample_size:
            score = 0
            state = env.reset()
            
            for _ in range(200):
                if args.render:
                    env.render()

                step += 1

                state = torch.Tensor(state)
                policies = actor(state.unsqueeze(0))
                action = get_action(policies) 
                next_state, reward, done, _ = env.step(action)
                irl_reward = get_reward(discrim, state, action)

                if done:
                    mask = 0
                else:
                    mask = 1

                memory.push(state, action, irl_reward, mask)
                
                score += reward
                state = next_state

                if done:
                    break
            
            episode += 1
            scores.append(score)
            episodes.append(episode)
            pylab.plot(episodes, scores, 'b')
            pylab.savefig("./learning_curves/gail_train.png")        
        
        score_avg = np.mean(scores)
        print('{} episode score is {:.2f}'.format(episode, score_avg))
        # writer.add_scalar('log/score', float(score_avg), iter)
        
        transitions = memory.sample()
        
        actor.train(), critic.train(), discrim.train()
        train_discrim(discrim, transitions, discrim_optim, demonstrations, device)
        train_actor_critic(actor, critic, transitions, actor_optim, critic_optim, args, device)
        
        # if iter % 20:
        #     ckpt_path = args.save_path + 'model.pth'
        #     torch.save({
        #         'actor': actor.state_dict(),
        #         'critic': critic.state_dict(),
        #         'discrim': discrim.state_dict(),
        #         }, ckpt_path)

if __name__ == '__main__':
    main()