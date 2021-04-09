from dataclasses import dataclass
from collections import abc
from typing import Union, Type, TypeVar, Generic, List


class InvalidChoiceError(Exception):
    pass

class RequiredError(Exception):
    pass

class ConditionError(Exception):
    pass

T = TypeVar('T')
class required: ...
Required = Union[Type[required], T]

class Condition(Generic[T]):
    def __init__(self, value: T, comp):
        self.value: T = value
        self.comp = comp

    def compare(self, config):
        return self.comp(config)

    def __and__(self, other):
        return Condition(self.value, lambda config: self.comp(config) and other.comp(config))

    def __or__(self, other):
        return Condition(self.value, lambda config: self.comp(config) or other.comp(config))

    def __invert__(self):
        return Condition(self.value, lambda config: not self.comp(config))

class Choices(Generic[T]):
    def __init__(self, choices, default=required):
        if default is not required:
            if default not in choices:
                raise InvalidChoiceError('Default value is not in choices')
        self.choices: List[T] = choices
        self.default: Required[T] = default

    def __get_value(self, config):
        value = config.get_config(self._name)
        if isinstance(value, Choices):
            return self.default
        else:
            return value

    def __eq__(self, other):
        return lambda config: self.__get_value(config) == other

    def __lt__(self, other):
        return lambda config: self.__get_value(config) < other

    def __le__(self, other):
        return lambda config: self.__get_value(config) <= other

    def __ne__(self, other):
        return lambda config: self.__get_value(config) != other

    def __gt__(self, other):
        return lambda config: self.__get_value(config) > other

    def __ge__(self, other):
        return lambda config: self.__get_value(config) >= other

class Config(dict):
    def __init__(self, dictionary={}):
        if isinstance(dictionary, Config):
            self._name = dictionary._name
        else:
            self._name = None
        super(Config, self).__init__(dictionary)

    def check_config(self):
        for k, v in self.items():
            if isinstance(v, Config):
                v.check_config()
            else:
                self.check_value(k, v)

    @staticmethod
    def check_value(key, value):
        if isinstance(value, Config):
            value.check_config()
        elif isinstance(value, Choices):
            if value.default is required:
                raise RequiredError(f'{key} is required!')
        elif value is required:
            raise RequiredError(f'{key} is required!')

    def get_config(self, key, check=False):
        value = dict.__getitem__(self, key)
        if isinstance(value, Condition):
            if value.compare(self):
                return value.value
        if check:
            check_value = object.__getattribute__(self, 'check_value')
            check_value(key, value)
        return value

    def __getitem__(self, key):
        return self.get_config(key)

    def __getattr__(self, key):
        try:
            return self.get_config(key)
        except KeyError:
            raise AttributeError(key)

    def to_dict(self, check=False):
        if check:
            self.check_config()
        config_dict = {}
        for k, v in self.items():
            if k == '_name' or k == '__annotations__':
                continue
            if isinstance(v, Config):
                config_dict[k] = v.to_dict(check)
            elif isinstance(v, Choices):
                config_dict[k] = v.default
            elif isinstance(v, Condition):
                if v.compare(self):
                    config_dict[k] = v.value
            else:
                config_dict[k] = v
        return config_dict

    def __setattr__(self, key, value):
        self[key] = value

    def add_config(self, cls, name=None):
        if self.get(name):
            if name is None:
                raise ValueError
            parent = self.get(name)
            config_class = type(cls.__name__, (Config,), dict(cls.__dict__))
            members = [var for var in vars(config_class) if not var.startswith('__')]
            if hasattr(config_class, '__annotations__'):
                _annotations = {**parent.__annotations__, **config_class.__annotations__}
            else:
                _annotations = parent.__annotations__
            if name is None:
                name = parent._name
            annotations = {}
            for member in members:
                if member in _annotations:
                    annotations[member] = _annotations[member]
            config_class.__annotations__ = annotations
            config_class._name = name
            datacls = dataclass(config_class)()
            datacls.__annotations__ = config_class.__annotations__
            merged_config = parent.update(Config(datacls))
            merged_config.check_config()
            self[name] = merged_config
        else:
            config_class = type(cls.__name__, (Config,), dict(cls.__dict__))
            config_class._name = name
            datacls = dataclass(config_class)()
            datacls.__annotations__ = config_class.__annotations__
            datacls = Config(datacls)
            self[name] = datacls
        for k, v in self[name].items():
            if isinstance(v, Choices):
                v._name = k
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
                if isinstance(v, Choices):
                    newdict[k] = v.default
                else:
                    newdict[k] = v
            else:
                if isinstance(self[k], Config):
                    newdict[k] = self[k].update(v)
                elif isinstance(self[k], abc.Mapping):
                    newdict[k] = {**self[k], **v}
                elif isinstance(self[k], Condition):
                    if self[k].compare(other):
                        newdict[k] = v
                elif isinstance(v, Choices):
                    if self[k].default is required:
                        raise RequiredError(f'{k} is required, valid choices: {self[k].choices}')
                    else:
                        newdict[k] = self[k].default
                elif isinstance(self[k], Choices):
                    if v not in self[k].choices:
                        raise InvalidChoiceError(f'{v} is not valid for {k}, valid choices: {self[k].choices}')
                    else:
                        newdict[k] = v
                else:
                    newdict[k] = v
        return Config(newdict)
