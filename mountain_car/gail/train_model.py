import torch
import numpy as np


def train_discrim(discrim, transitions, discrim_optim, demonstrations, device):
    states = torch.stack(transitions.state).to(device)
    actions = torch.Tensor(transitions.action).unsqueeze(1).to(device)

    criterion = torch.nn.BCELoss()

    for _ in range(1):
        expert_state_action = torch.Tensor(demonstrations).to(device)
        
        learner = discrim(torch.cat([states, actions], dim=1))
        expert = discrim(expert_state_action)

        discrim_loss = criterion(learner, torch.ones((states.shape[0], 1), device=device)) + \
                        criterion(expert, torch.zeros((demonstrations.shape[0], 1), device=device))
        
        discrim_optim.zero_grad()
        discrim_loss.backward()
        discrim_optim.step()

        
def train_actor_critic(actor, critic, transitions, actor_optim, critic_optim, args, device):
    states = torch.stack(transitions.state).to(device)
    actions = torch.LongTensor(transitions.action).to(device)
    rewards = torch.Tensor(transitions.reward).to(device)
    masks = torch.Tensor(transitions.mask).to(device)

    # ----------------------------
    # step 1: get returns and GAEs and log probability of old policy
    old_values = critic(states)
    returns, advants = get_gae(rewards, masks, old_values, args, device)

    policies = actor(states)
    old_policy = policies[range(len(actions)), actions]
    
    criterion = torch.nn.MSELoss()
    n = len(states)
    arr = np.arange(n)
    
    # ----------------------------
    # step 2: get value loss and actor loss and update actor & critic
    for _ in range(10):
        np.random.shuffle(arr)
        
        for i in range(n // args.batch_size): 
            batch_index = arr[args.batch_size * i : args.batch_size * (i + 1)]
            batch_index = torch.LongTensor(batch_index).to(device)
            
            inputs = states[batch_index]
            actions_samples = actions[batch_index]
            returns_samples = returns.unsqueeze(1)[batch_index]
            advants_samples = advants.unsqueeze(1)[batch_index]
            oldvalue_samples = old_values[batch_index].detach()

            values = critic(inputs)
            clipped_values = oldvalue_samples + \
                             torch.clamp(values - oldvalue_samples,
                                         -args.clip_param, # 0.2
                                         args.clip_param)
            critic_loss1 = criterion(clipped_values, returns_samples)
            critic_loss2 = criterion(values, returns_samples)
            critic_loss = torch.max(critic_loss1, critic_loss2).mean()

            loss, ratio, entropy = surrogate_loss(actor, advants_samples, inputs,
                                         old_policy.detach(), actions_samples,
                                         batch_index)

            clipped_ratio = torch.clamp(ratio,
                                        1.0 - args.clip_param,
                                        1.0 + args.clip_param)
            clipped_loss = clipped_ratio * advants_samples
            actor_loss = -torch.min(loss, clipped_loss).mean()
        
            loss = actor_loss + 0.5 * critic_loss - 0.01 * entropy.sum().mean()

            critic_optim.zero_grad()
            loss.backward(retain_graph=True) 
            critic_optim.step()

            actor_optim.zero_grad()
            loss.backward()
            actor_optim.step()

def get_gae(rewards, masks, values, args, device):
    returns = torch.zeros_like(rewards).to(device)
    advants = torch.zeros_like(rewards).to(device)
    
    running_returns = 0
    previous_value = 0
    running_advants = 0

    for t in reversed(range(0, len(rewards))):
        running_returns = rewards[t] + (args.gamma * running_returns * masks[t])
        returns[t] = running_returns

        running_delta = rewards[t] + (args.gamma * previous_value * masks[t]) - \
                                        values.data[t]
        previous_value = values.data[t]
        
        running_advants = running_delta + (args.gamma * args.lamda * \
                                            running_advants * masks[t])
        advants[t] = running_advants

    advants = (advants - advants.mean()) / advants.std()
    return returns, advants

def surrogate_loss(actor, advants, states, old_policy, actions, batch_index):
    policies = actor(states)
    new_policy = policies[range(len(actions)), actions]
    old_policy = old_policy[batch_index]

    ratio = torch.exp(new_policy - old_policy)
    surrogate_loss = ratio * advants
    entropy = policies * torch.log(policies)

    return surrogate_loss, ratio, entropy