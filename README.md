PIPCS: PIPCS is Python Configuration System
-------------------------------------------
![Test](https://github.com/goktug97/pipcs/actions/workflows/python-package.yml/badge.svg)

pipcs is an experimental library to create configuration files for Python.

# Installation

```bash
pip install pipcs --user
```

# Documentation
https://pipcs.readthedocs.io/

# Example Scenario

- In some_program.py:
```python
from dataclasses import field
from typing import Dict, Type, Callable, Union, List

import torch
import numpy as np
import gym

from pipcs import Config, Choices, Condition, Required, required

default_config = Config()

@default_config('optimizer')
class OptimizerConfig():
    optim_type: Choices[Type[torch.optim.Optimizer]] = Choices([torch.optim.Adam, torch.optim.SGD], default=torch.optim.Adam)
    weight_decay: float = 0.0
    lr: float = 0.001
    betas: Condition[Tuple[float, float]] = Condition((0.9, 0.999), optim_type == torch.optim.Adam)
    eps: Condition[float] = Condition(1e-08, optim_type == torch.optim.Adam)
    momentum: Condition[float] = Condition(0.0, optim_type == torch.optim.SGD)
    dampening: Condition[float] = Condition(0.0, optim_type == torch.optim.SGD)

@default_config('environment')
class EnvironmentConfig():
    env_id: Required[str] = required

@default_config('policy')
class PolicyConfig():
    input_size: Required[int] = required
    hidden_layers: List[int] = field(default_factory=lambda: [])
    output_size: Required[int] = required
    output_func: Required[Callable[[torch.Tensor], Union[int, np.ndarray]]] = required
    activation: torch.nn.Module = torch.nn.ReLU

class Policy(torch.nn.Module):
    def __init__(self, input_size, hidden_layers, output_size, activation, output_func):
        super().__init__()
        self.seq = torch.nn.Sequential(
            torch.nn.Linear(input_size, 64),
            activation(),
            torch.nn.Linear(64, 64),
            activation(),
            torch.nn.Linear(64, output_size))

class ReinforcementLearning():
    def __init__(self, config: Config = default_config):
        self.config = config
        self.policy = Policy(**config.policy.to_dict())
        self.optim = self.make_optimizer(parameters=self.policy.parameters(), **config.optimizer.to_dict())
        self.env = gym.make(config.environment.env_id)

    def make_optimizer(self, optim_type, parameters, **kwargs):
        return optim_type(parameters, **kwargs)
```

- In user file:
```python
from pipcs import Config, Condition

import gym
import torch
from dataclasses import field

from some_program import default_config, ReinforcementLearning

user_config = Config(default_config)

@user_config('optimizer')
class UserOptimizerConfig():
    optim_type = torch.optim.Adam
    # Users can add their own variables too
    amsgrad: Condition[bool] = Condition(False, default_config.optimizer.optim_type == torch.optim.Adam)
    nesterov: Condition[bool] = Condition(False, default_config.optimizer.optim_type == torch.optim.SGD)

@user_config('environment')
class UserEnvironmentConfig():
    env_id = 'CartPole-v1'

@user_config('policy')
class UserPolicyConfig():
    env = gym.make(user_config.environment.env_id)
    input_size = env.observation_space.shape[0]
    hidden_layers = field(default_factory=lambda: [64, 32])
    if isinstance(env.action_space, gym.spaces.Discrete):
        output_size = env.action_space.n
        output_func = lambda x: x.argmax().item()
    else:
        output_size = env.action_space.shape[0]
        output_func = lambda x: x.detach().numpy()

ReinforcementLearning(user_config)
```

- *Note*: If a config is not inherited, `typing` is necessary. Also, if you are adding your own variable to the inherited config and want it to be register, you need to specify the type. Putting the correct type is not necessary. `'typing.Any'` can be used if you don't want to bother with `typing` but they are important if you are using a static type checking tool such as `mypy`.

## Accessing Variables
```python
>>> from pipcs import Config
>>> 
>>> config = Config()
>>> 
>>> @config.add('configuration')
... class Foo():
...     bar: str = 'bar'
...     baz: int = 1
... 
>>> print(config.configuration.bar)
bar
>>> print(config.configuration.baz)
1
>>> print(config['configuration']['bar'])
bar
```
