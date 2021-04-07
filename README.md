PIPCS: PIPCS is Python Configuration System
-------------------------------------------

pipcs is an experimental library to create configuration files for Python.

# Installation

```bash
pip install pipcs --user
```

# Example Scenario

- In some_program.py:
```python
from dataclasses import field
from typing import Dict, Type, Callable, Union, List, Optional

import torch
import numpy as np
import gym

from pipcs import Config, Choices, Required

default_config = Config()

@default_config.add('optimizer')
class OptimizerConfig():
    optim_type: Type[torch.optim.Optimizer] = Choices([torch.optim.Adam, torch.optim.SGD])
    lr: float = 0.001

@default_config.add('environment')
class EnvironmentConfig():
    env_id: str = Required

@default_config.add('policy')
class PolicyConfig():
    input_size: int = Required
    hidden_layers: List[int] = field(default_factory=lambda: [])
    output_size: int = Required
    output_func: Callable[[torch.Tensor], Union[int, np.ndarray]] = Required
    activation: torch.nn.Module = torch.nn.ReLU

class ReinforcementLearning():
    def __init__(self, config: Optional[Config] = None):
        if config is not None:
            self.config = default_config.update(config)
        else:
            self.config = config
        ...
        print(self.config)
```

- In user file:
```python
from pipcs import Config

import gym
import torch
from dataclasses import field

from some_program import default_config, ReinforcementLearning

user_config = Config()

@user_config.inherit(default_config.optimizer)
class UserOptimizerConfig():
    optim_type = torch.optim.Adam

@user_config.inherit(default_config.environment)
class UserEnvironmentConfig():
    env_id: str = 'CartPole-v1'

@user_config.inherit(default_config.policy)
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
