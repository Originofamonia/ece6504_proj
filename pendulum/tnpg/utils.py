import math
import torch
from torch.distributions import Normal

def get_action(mu, std):
    m = Normal(mu, std)
    action = m.sample()
    action = action.data.numpy()
    return action


def get_returns(rewards, masks, gamma):
    rewards = torch.Tensor(rewards)
    masks = torch.Tensor(masks)
    returns = torch.zeros_like(rewards)

    running_returns = 0

    for t in reversed(range(0, len(rewards))):
        running_returns = rewards[t] + gamma * running_returns * masks[t]
        returns[t] = running_returns

    returns = (returns - returns.mean()) / returns.std()
    return returns


def get_loss(actor, returns, states, actions):
    mu, std = actor(torch.Tensor(states))
    log_policy = log_prob_density(torch.Tensor(actions), mu, std)
    returns = returns.unsqueeze(1)

    loss = log_policy * returns
    loss = loss.mean()
    return loss

def log_prob_density(x, mu, std):
    log_density = -(x - mu).pow(2) / (2 * std.pow(2)) \
                    - 0.5 * math.log(2 * math.pi)
    return log_density.sum(1, keepdim=True)


# from openai baseline code
# https://github.com/openai/baselines/blob/master/baselines/common/cg.py
def conjugate_gradient(actor, states, b, nsteps, residual_tol=1e-10):
    x = torch.zeros(b.size())
    r = b.clone()
    p = b.clone()
    rdotr = torch.dot(r, r)

    for i in range(nsteps): # nsteps = 10
        f_Ax = hessian_vector_product(actor, states, p, cg_damping=1e-1)
        alpha = rdotr / torch.dot(p, f_Ax)

        x += alpha * p
        r -= alpha * f_Ax
        
        new_rdotr = torch.dot(r, r)
        betta = new_rdotr / rdotr

        p = r + betta * p
        rdotr = new_rdotr
        
        if rdotr < residual_tol: # residual_tol = 0.0000000001
            break
    return x

def hessian_vector_product(actor, states, p, cg_damping):
    p.detach() 
    kl = kl_divergence(old_actor=actor, new_actor=actor, states=states)
    kl = kl.mean()
    
    kl_grad = torch.autograd.grad(kl, actor.parameters(), create_graph=True)
    kl_grad = flat_grad(kl_grad)

    kl_grad_p = (kl_grad * p).sum()
    kl_hessian = torch.autograd.grad(kl_grad_p, actor.parameters())
    kl_hessian = flat_hessian(kl_hessian)

    return kl_hessian + p * cg_damping # cg_damping = 0.1

def kl_divergence(old_actor, new_actor, states):
    mu, std = new_actor(torch.Tensor(states))
    mu_old, std_old = old_actor(torch.Tensor(states))
    mu_old = mu_old.detach()
    std_old = std_old.detach()

    # kl divergence between old policy and new policy : D( pi_old || pi_new )
    # pi_old -> mu_old, std_old / pi_new -> mu, std
    # be careful of calculating KL-divergence. It is not symmetric metric.
    kl = torch.log(std / std_old) + (std_old.pow(2) + (mu_old - mu).pow(2)) / (2.0 * std.pow(2)) - 0.5
    return kl.sum(1, keepdim=True)


def flat_grad(grads):
    grad_flatten = []
    for grad in grads:
        grad_flatten.append(grad.view(-1))
    grad_flatten = torch.cat(grad_flatten)
    return grad_flatten

def flat_hessian(hessians):
    hessians_flatten = []
    for hessian in hessians:
        hessians_flatten.append(hessian.contiguous().view(-1))
    hessians_flatten = torch.cat(hessians_flatten).data
    return hessians_flatten


def flat_params(model):
    params = []
    for param in model.parameters():
        params.append(param.data.view(-1))
    params_flatten = torch.cat(params)
    return params_flatten

def update_model(model, new_params):
    index = 0
    for params in model.parameters():
        params_length = len(params.view(-1))
        new_param = new_params[index: index + params_length]
        new_param = new_param.view(params.size())
        params.data.copy_(new_param)
        index += params_length