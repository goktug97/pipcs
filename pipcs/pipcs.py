import os
import types
from dataclasses import dataclass
from collections import abc
from typing import Union, Type, TypeVar, Generic, List


class InvalidChoiceError(Exception):
    """Raised when the user tries to assign a non-valid variable to :class:`pipcs.Choices` variable."""
    pass


class RequiredError(Exception):
    """Raised if a user doesn't set :class:`pipcs.required` variable
       in the inherited config. It is also raised if a :class:`pipcs.required`
       variable is not set during :meth:`pipcs.Config.check_config`.
    """
    pass


class ConditionError(Exception):
    pass


T = TypeVar('T')


class required:
    """Mark a variable as required."""
    pass


Required = Union[Type[required], T]


class Comparison():
    def __init__(self, comp):
        self.comp = comp

    def __and__(self, other):
        return Comparison(lambda config: self.comp(config) and other.comp(config))

    def __or__(self, other):
        return Comparison(lambda config: self.comp(config) or other.comp(config))

    def __invert__(self):
        return Comparison(lambda config: not self.comp(config))

    def __call__(self, config):
        return self.comp(config)


class Comparable():
    def __init__(self, data):
        self.data = data

    def _get_value(self, config):
        value = config.get_value(self._name)
        if isinstance(value, Comparable):
            return self.data
        else:
            return value

    def __eq__(self, other):
        return Comparison(lambda config: self._get_value(config) == other)

    def __lt__(self, other):
        return Comparison(lambda config: self._get_value(config) < other)

    def __le__(self, other):
        return Comparison(lambda config: self._get_value(config) <= other)

    def __ne__(self, other):
        return Comparison(lambda config: self._get_value(config) != other)

    def __gt__(self, other):
        return Comparison(lambda config: self._get_value(config) > other)

    def __ge__(self, other):
        return Comparison(lambda config: self._get_value(config) >= other)


class Condition(Generic[T]):
    """Mark a variable as valid, only if the condition is hold. It is used combined with :class:`pipcs.Choices`.

    Args:
        data (T): Value of the variable.
        comp: Comparison function.

    .. code-block:: python

        from pipcs import Config, Choices, Condition

        config = Config()

        @config('example')
        class Example():
            variable: Choices[int] = Choices([1, 2, 3])
            conditional_variable: Condition[int] = Condition(5, variable==2)

        # Example 1
        user_config = Config(config)

        @user_config('example')
        class UserExample():
            variable = 2

        print(user_config.example.to_dict())
        # {'variable': 2, 'conditional_variable': 5}

        # Example 2
        user_config = Config(config)

        @user_config('example')
        class UserExample():
            variable = 2
            conditional_variable = 1

        print(user_config.example.to_dict())
        # {'variable': 2, 'conditional_variable': 1}

        # Example 3
        user_config = Config(config)

        @user_config('example')
        class UserExample():
            variable = 1
            conditional_variable = 2

        print(user_config.example.to_dict())
        # {'variable': 1}
    """
    def __init__(self, data: T, comp: Comparison):
        self.data: T = data
        self.comp = comp


class Choices(Comparable, Generic[T]):
    """Specify valid choices for a variable.
       :class:`pipcs.InvalidChoiceError` error will be raised when the user
        tries to set the variable to a non-valid choice in the inherited configuration.

    Args:
        choices (List[T]): Valid choices for the configuration variable.
        default (Required[T]): If the variable is not set by user the default value will be returned.

    .. code-block:: python

        from pipcs import Config, Choices

        config = Config()

        @config('example')
        class Example():
            variable: Choices[int] = Choices([1, 2, 3])

        user_config = Config(config)

        @user_config('example')
        class UserExample():
            variable = 1

        print(user_config.example.variable)
        # 1

        user_config = Config(config)

        @user_config('example')
        class UserExample():
            variable = 4
        # Raises: pipcs.pipcs.InvalidChoiceError: 4 is not valid for variable, valid choices: [1, 2, 3]
    """
    def __init__(self, choices: List[T], default=required):
        if default is not required:
            if default not in choices:
                raise InvalidChoiceError('Default value is not in choices')
        self.choices: List[T] = choices
        self.data: Required[T] = default
        super().__init__(self.data)


class Config(dict):
    """Base class to create root configuration.

    Args:
        dictionary (:obj:`Union[dict, Config]`, optional): If it is a :class:`pipcs.Config`,
                                                           it will inherit the base configuration.
    """
    def __init__(self, dictionary={}):
        if isinstance(dictionary, Config):
            self._name = dictionary._name
        else:
            self._name = None
        super(Config, self).__init__(dictionary)

    def check_config(self):
        """Check configuration if all of the variables are valid.

        .. code-block:: python

            from pipcs import Config, Required, required

            config = Config()

            @config('example')
            class Example():
                variable: Required[int] = required

            config.check_config()
            # Raises: pipcs.pipcs.RequiredError: variable is required!
        """

        for k, v in self.items():
            if isinstance(v, Config):
                v.check_config()
            else:
                self.check_value(k, v)

    def check_value(self, key, value):
        if isinstance(value, Config):
            value.check_config()
        elif isinstance(value, Choices):
            if value.data is required:
                raise RequiredError(f'{key} is required!')
        elif isinstance(value, Condition):
            if value.comp(self):
                if value.data is required:
                    raise RequiredError(f'{key} is required!')
        elif value is required:
            raise RequiredError(f'{key} is required!')

    def get_value(self, key, check=False):
        """
        Return value of the variable.

        Args:
            check (bool): If true, the variable will be checked if it is valid or not.

        .. code-block:: python

            from pipcs import Config, Required, required

            config = Config()

            @config('example')
            class Example():
                variable: Required[int] = required

            print(config.example.get_value('variable'))
            # <class 'pipcs.pipcs.required'>

            print(config.example.get_value('variable', check=True))
            # pipcs.pipcs.RequiredError: variable is required!
        """
        value = dict.__getitem__(self, key)
        if check:
            check_value = object.__getattribute__(self, 'check_value')
            check_value(key, value)
        return value

    def __getitem__(self, key):
        return self.get_value(key)

    def __getattr__(self, key):
        try:
            return self.get_value(key)
        except KeyError:
            raise AttributeError(key)

    def to_dict(self, check=False):
        """
        Convert :class:`pipcs.Config` to :class:`dict`.
        If the :class:`pipcs.Condition` holds for a variable it will be included in the dictionary.
        :class:`pipcs.Choices` variables will be converted in to their default values.

        Args:
            check (bool): If true, the variables will be checked if they are valid or not.
        """

        if check:
            self.check_config()
        config_dict = {}
        for k, v in self.items():
            if k == '_name' or k == '__annotations__':
                continue
            if isinstance(v, Config):
                config_dict[k] = v.to_dict(check)
            elif isinstance(v, Comparable):
                config_dict[k] = v.data
            elif isinstance(v, Condition):
                if v.comp(self):
                    config_dict[k] = v.data
            else:
                config_dict[k] = v
        return config_dict

    def __setattr__(self, key, value):
        self[key] = value

    def add_config(self, cls, name, check=True):
        if self.get(name):
            parent = self.get_value(name)
            config_class = type(cls.__name__, (Config,), dict(cls.__dict__))
            members = [var for var in vars(config_class) if not var.startswith('__')]
            if hasattr(config_class, '__annotations__'):
                _annotations = {**parent.__annotations__, **config_class.__annotations__}
            else:
                _annotations = parent.__annotations__
            annotations = {}
            for member in members:
                if member in _annotations:
                    annotations[member] = _annotations[member]
            config_class.__annotations__ = annotations
            config_class._name = name
            datacls = dataclass(config_class)()
            datacls.__annotations__ = config_class.__annotations__
            merged_config = parent.update_config(Config(datacls))
            if check:
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
            if isinstance(v, Comparable):
                v._name = k
        return self[name]

    def add(self, name, check=True):
        def _add(wrapped_class):
            self.add_config(wrapped_class, name, check)
            return wrapped_class
        return _add

    def __call__(self, name, check=True):
        return self.add(name, check)

    def _update_comparables(self, other):
        for k, v in other.items():
            if isinstance(v, Config):
                self[k]._update_comparables(v)
            elif isinstance(self[k], Comparable):
                self[k] = v.data

    def update_config(self, other):
        newdict = Config(self)
        for k, v in other.items():
            newdict[k] = v
            if hasattr(self, k):
                if isinstance(self[k], Config):
                    newdict[k] = self[k].update_config(v)
                elif isinstance(self[k], abc.Mapping):
                    newdict[k] = {**self[k], **v}
                elif isinstance(self[k], Choices):
                    if v not in self[k].choices:
                        raise InvalidChoiceError(f'{v} is not valid for {k}, valid choices: {self[k].choices}')
                elif isinstance(self[k], Condition):
                    newdict[k] = Condition(v, self[k].comp)

        newdict._update_comparables(self)
        return newdict


def read_config(config_file, config_name=None):
    """Read a config from a file. Basically works as `import` but you can load files
    from different locations by path.

    Args:
        config_file (str): File path
        config_name (str): If given only the given attribute will be returned instead of whole module.
    """
    base = os.path.basename(config_file)
    module = os.path.splitext(base)[0]
    config = types.ModuleType(module, 'Config')
    with open(config_file) as f:
        code = f.read()
        code = compile(code, module, "exec")
        exec(code, config.__dict__)
    if config_name is not None:
        return getattr(config, config_name)
    else:
        return config
