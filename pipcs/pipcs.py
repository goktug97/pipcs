from dataclasses import dataclass, field, asdict
from collections import defaultdict, abc


class InvalidChoiceError(Exception):
    pass

class RequiredError(Exception):
    pass

Required = object()

class Choices():
    def __init__(self, choices, default=Required):
        if default is not Required:
            if default not in choices:
                raise InvalidChoiceError('Default value is not in choices')
        self.choices = choices
        self.default = default

class Config(dict):
    def __init__(self, dictionary={}):
        super(Config, self).__init__(dictionary)
        self.__name = None

    def check_config(self, config):
        for k, v in config.items():
            if isinstance(v, Config):
                self.check_config(v)
            else:
                self.check_value(k, v)

    @staticmethod
    def check_value(key, value):
        if isinstance(value, Choices):
            if value.default is Required:
                raise RequiredError(f'{key} is required!')
            else:
                return value.default
        elif value is Required:
            raise RequiredError(f'{key} is required!')
        else:
            return value

    def __getattr__(self, key):
        try:
            value = self[key]
            return self.check_value(key, value)
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def add(self, name=None):
        def _add(wrapped_class):
            _name = name
            if not self.get(_name):
                parent = wrapped_class.__bases__[0]
                if hasattr(parent, '__annotations__') and issubclass(parent, Config):
                    members = [var for var in vars(wrapped_class) if not var.startswith('__')]
                    _annotations = {**parent.__annotations__, **wrapped_class.__annotations__}
                    if name is None:
                        _name = parent.__name
                    annotations = {}
                    for member in members:
                        if member in _annotations:
                            annotations[member] = _annotations[member]
                    wrapped_class.__annotations__ = annotations
                config_class = type(wrapped_class.__name__,
                        (Config,), dict(wrapped_class.__dict__))
                config_class.__name = _name
                self[_name] = dataclass(config_class)()
                return config_class
            else:
                raise AttributeError(f'"{name}" is already added for class "{self[name].__class__.__name__}"')
        return _add

    def inherit(self, cls):
        def _inherit(wrapped_class):
            config_class = type(wrapped_class.__name__,
                    (cls.__class__,), dict(wrapped_class.__dict__))
            return self.add()(config_class)
        return _inherit

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
                else:
                    if isinstance(self[k], Choices):
                        if v not in self[k].choices:
                            raise InvalidChoiceError(f'Valid choices: {self[k].choices}')
                    newdict[k] = v
        config = Config(newdict)
        self.check_config(config)
        return config
