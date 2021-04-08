from dataclasses import dataclass, field, asdict
from collections import defaultdict, abc
from typing import Union, Type, TypeVar, Generic, List


class InvalidChoiceError(Exception):
    pass

class RequiredError(Exception):
    pass

T = TypeVar('T')
class required: ...
Required = Union[Type[required], T]

class Choices(Generic[T]):
    def __init__(self, choices, default=required):
        if default is not required:
            if default not in choices:
                raise InvalidChoiceError('Default value is not in choices')
        self.choices: List[T] = choices
        self.default: Required[T] = default

class Config(dict):
    def __init__(self, dictionary={}):
        if isinstance(dictionary, Config):
            self.__name = dictionary.__name
        else:
            self.__name = None
        super(Config, self).__init__(dictionary)

    def check_config(self, config):
        for k, v in config.items():
            if isinstance(v, Config):
                self.check_config(v)
            else:
                self.check_value(k, v)

    def check_value(self, key, value):
        if isinstance(value, Config):
            self.check_config(value)
        elif isinstance(value, Choices):
            if value.default is required:
                raise RequiredError(f'{key} is required!')
        elif value is required:
            raise RequiredError(f'{key} is required!')

    def __getattr__(self, key):
        value = self[key]
        self.check_value(key, value)
        return value

    def to_dict(self):
        self.check_config(self)
        config_dict = {}
        for k, v in self.items():
            if k == '_Config__name':
                continue
            if isinstance(v, Config):
                config_dict[k] = v.to_dict()
            elif isinstance(v, Choices):
                config_dict[k] = v.default
            else:
                config_dict[k] = v
        return config_dict

    def __setattr__(self, key, value):
        self[key] = value

    def add_config(self, cls, name=None):
        if self.get(name):
            parent = self.get(name)
            config_class = type(cls.__name__, (parent.__class__,), dict(cls.__dict__))
            data_class = self.add_config(config_class)
            merged_config = parent.update(self[data_class.__name])
            self.check_config(merged_config)
            self[data_class.__name] = merged_config
            return self[data_class.__name]

        parent = cls.__bases__[0]
        if hasattr(parent, '__annotations__') and issubclass(parent, Config):
            members = [var for var in vars(cls) if not var.startswith('__')]
            _annotations = {**parent.__annotations__, **cls.__annotations__}
            if name is None:
                name = parent.__name
            annotations = {}
            for member in members:
                if member in _annotations:
                    annotations[member] = _annotations[member]
            cls.__annotations__ = annotations
            cls.__name = name
            datacls = dataclass(cls)()
        else:
            config_class = type(cls.__name__, (Config,), dict(cls.__dict__))
            config_class.__name = name
            datacls = dataclass(config_class)()
        self[name] = datacls
        return self[name]

    def add(self, name=None):
        def _add(wrapped_class):
            return self.add_config(wrapped_class, name)
        return _add

    def __call__(self, name=None):
        return self.add(name)

    def update(self, other):
        newdict = dict(self)
        for k, v in other.items():
            if not hasattr(self, k):
                newdict[k] = v
            else:
                if isinstance(self[k], Config):
                    newdict[k] = self[k].update(v)
                elif isinstance(self[k], abc.Mapping):
                    newdict[k] = {**self[k], **v}
                elif isinstance(self[k], Choices):
                    if v not in self[k].choices:
                        if self[k].default is not required:
                            print(f'Warning: {k} is invalid, using default value {self[k].default}, valid choices: {self[k].choices}')
                            newdict[k] = self[k].default
                            continue
                        raise InvalidChoiceError(f'Valid choices: {self[k].choices}')
                    else:
                        newdict[k] = v
                else:
                    newdict[k] = v
        config = Config(newdict)
        return config
