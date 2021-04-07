from dataclasses import dataclass, field, asdict
from typing import Dict
from collections import defaultdict, abc

class Config(defaultdict):
    def __init__(self, dictionary={}):
        super(Config, self).__init__(Config, dictionary)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def register(self, name):
        def _register(wrapped_class):
            if not self.get(name):
                config_class = type(wrapped_class.__name__,
                        (Config,), dict(wrapped_class.__dict__))
                self[name] = dataclass(config_class)()
                return wrapped_class
            else:
                raise AttributeError(f'"{name}" is already registered for class "{self[name].__class__.__name__}"')
        return _register

    def update(self, other):
        newdict = dict(self)
        for k, v in other.items():
            if not hasattr(self, k):
                newdict[k] = v
            else:
                if isinstance(self[k], Config):
                    newdict[k] = self[k].update(v)
                elif isinstance(self[k], abc.Mapping):
                    newdict[k] = self[k] | v
                else:
                    newdict[k] = v
        return Config(newdict)

config = Config()

@config.register('optimizer')
class A():
    a: int = 5
    b: Dict[str, int] = field(default_factory = lambda: {'a': 12, 'b': 5, 'c':3})
    # b: 'Test' = namedtuple('Test', ['a', 'c'], defaults=[12, 3])

@config.register('test')
@config.register('policy')
class B():
    b: int = config.optimizer.a + 1
    e: int = 10


@config.policy.register('another')
class C():
    c: int = config.policy.b + 1

co = Config()

@co.register('optimizer')
class D():
    a: int = 5
    b: Dict[str, int] = field(default_factory = lambda: {'a': 15, 'c':3, 'd': 45})

@co.register('test')
@co.register('policy')
class E():
    b: int = 30
    d: str = 'a'


@co.policy.register('another')
class F():
    c: int = co.policy.b + 2

# print(config['policy']['b'])
# print(config.policy.b)
# print(config.policy.another.c)
# print(config.test.b)
# print(config.optimizer.a)
# print(config['optimizer']['a'])
# config|config

config = config.update(co)
print()
print(config.policy.e)
print(config.policy.d)
print()
print(config.policy.b)
print(co.policy.b)
print()
print(config.policy.another.c)
print(co.policy.another.c)

print(config.optimizer.b)
print(co.optimizer.b)
print()
print(config)
# print(config.policy.e)
# config.update(co)
# print(config.policy.e)
# print(config)



