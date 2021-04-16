import unittest

from pipcs import Config, Choices, Condition, required, Required
from pipcs import InvalidChoiceError, RequiredError

class TestChoices(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        @self.config('test')
        class Test():
            variable1: Choices[int] = Choices([1, 2, 3])
            variable2: Choices[int] = Choices([1, 2, 3], default=1)

    def test_default(self):
        self.assertEqual(self.config.test.variable1.data, required)
        self.assertEqual(self.config.test.variable2.data, 1)

        config = Config(self.config)
        @config('test')
        class Test():
            variable1 = 1
        self.assertEqual(config.test.variable2, 1)

    def test_valid_default(self):
        config = Config()
        with self.assertRaises(InvalidChoiceError):
            @config('test')
            class Test():
                variable: Choices[int] = Choices([1, 2, 3], default=4)

    def test_required_error(self):
        with self.assertRaises(RequiredError):
            self.config.test.get_value('variable1', check=True)

        config = Config(self.config)
        with self.assertRaises(RequiredError):
            @config('test')
            class Test():
                variable2 = 1

    def test_to_dict(self):
        config = self.config.to_dict()
        self.assertEqual(config['test']['variable1'], required)
        self.assertEqual(config['test']['variable2'], 1)

    def test_invalid_choices(self):
        config = Config(self.config)
        with self.assertRaises(InvalidChoiceError):
            @config('test')
            class Test():
                variable1 = 4


class TestCondition(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        @self.config('test')
        class Test():
            variable1: Choices[int] = Choices([1, 2, 3], default=3)
            variable2: Choices[int] = Choices([1, 2, 3], default=1)
            conditional_variable1: Condition[Required[int]] = Condition(required, variable1 == 1)
            conditional_variable2: Condition[int] = Condition(1, variable1 == 2)
            conditional_variable3: Condition[Required[int]] = Condition(required, variable1 == 3)
            conditional_variable4: Condition[int] = Condition(1, (variable1 == 3) & (variable2 == 1))
            conditional_variable5: Condition[int] = Condition(1, (variable1 == 3) | (variable2 == 1))
            conditional_variable6: Condition[int] = Condition(1, ~(variable1 == 3))

        self.user_config1 = Config(self.config)
        @self.user_config1('test')
        class Test():
            variable1 = 1
            conditional_variable1 = 2
            conditional_variable2 = 2

        self.user_config2 = Config(self.config)
        @self.user_config2('test')
        class Test():
            variable1 = 2

    def test_value(self):
        self.assertEqual(self.user_config1.test.conditional_variable1.data, 2)
        self.assertEqual(self.config.test.conditional_variable1.data, required)
        self.assertEqual(self.user_config2.test.conditional_variable2.data, 1)
        self.assertEqual(self.config.test.conditional_variable3.data, required)

    def test_in(self):
        self.assertTrue('conditional_variable1' in self.user_config1.test.to_dict())
        self.assertFalse('conditional_variable1' in self.user_config2.test.to_dict())
        self.assertTrue('conditional_variable3' in self.config.test.to_dict())

        self.assertTrue('conditional_variable2' in self.user_config2.test.to_dict())
        self.assertFalse('conditional_variable2' in self.user_config1.test.to_dict())

    def test_required_error(self):
        with self.assertRaises(RequiredError):
            self.config.to_dict(check=True)

        try:
            self.user_config2.test.to_dict(check=True)
        except RequiredError:
            self.fail('Raised RequiredError')

        with self.assertRaises(RequiredError):
            config = Config(self.config)
            @config('test')
            class Test():
                variable1 = 1

        try:
            config = Config(self.config)
            @config('test')
            class Test():
                variable1 = 2
        except RequiredError:
            self.fail('Raised RequiredError')

    def test_logic(self):
        config = Config(self.config)
        @config('test')
        class Test():
            conditional_variable3 = 1
            variable1 = 3
            variable2 = 1

        self.assertTrue('conditional_variable4' in config.test.to_dict())
        self.assertTrue('conditional_variable5' in config.test.to_dict())
        self.assertFalse('conditional_variable6' in config.test.to_dict())

        config = Config(self.config)
        @config('test')
        class Test():
            conditional_variable1 = 1
            variable1 = 1
            variable2 = 1

        self.assertFalse('conditional_variable4' in config.test.to_dict())
        self.assertTrue('conditional_variable5' in config.test.to_dict())
        self.assertTrue('conditional_variable6' in config.test.to_dict())

        config = Config(self.config)
        @config('test')
        class Test():
            conditional_variable1 = 1
            variable1 = 1
            variable2 = 3

        self.assertFalse('conditional_variable4' in config.test.to_dict())
        self.assertFalse('conditional_variable5' in config.test.to_dict())
        self.assertTrue('conditional_variable6' in config.test.to_dict())

        config = Config(self.config)
        @config('test')
        class Test():
            conditional_variable3 = 1
            variable1 = 3
            variable2 = 3

        self.assertFalse('conditional_variable4' in config.test.to_dict())
        self.assertTrue('conditional_variable5' in config.test.to_dict())
        self.assertFalse('conditional_variable6' in config.test.to_dict())


class TestRequired(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        @self.config('test')
        class Test():
            variable: int = 2
            required_variable: Required[int] = required

    def test_inherit(self):
        with self.assertRaises(RequiredError):
            config = Config(self.config)
            @config('test')
            class Test():
                variable = 1
        try:
            config = Config(self.config)
            @config('test')
            class Test():
                required_variable = 1
        except RequiredError:
            self.fail('Raised RequiredError')

    def test_to_dict(self):
        with self.assertRaises(RequiredError):
            self.config.to_dict(check=True)

        config = self.config.to_dict()
        self.assertEqual(self.config.test.required_variable, required)
        self.assertEqual(config['test']['required_variable'], required)


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        @self.config('test')
        class Test():
            variable: int = 1
            choice_variable: Choices[int] = Choices([1, 2, 3], default=1)

    def test_missing(self):
        with self.assertRaises(AttributeError):
            self.config.test.missing_variable

        with self.assertRaises(AttributeError):
            self.config.missing_config

    def test_get_value(self):
        self.config.get_value('test', check=True)

    def test_to_dict(self):
        self.config.to_dict(check=True)

    def test_user_variables(self):
        config = Config(self.config)
        @config('test')
        class Test():
            user_variable: int = 2
            no_typing_variable = 1
        self.assertEqual(config.test.variable, 1)
        self.assertEqual(config.test.user_variable, 2)
        self.assertFalse(hasattr(config.test, 'no_typing_variable'))

    def test_default_choice(self):
        config = Config(self.config)
        self.assertTrue(isinstance(config.test.choice_variable, Choices))
        @config('test')
        class Test():
            pass

    def test_update(self):
        config = Config()
        @config('test')
        class Test():
            variable: int = 2
            choice_variable2: Choices[int] = Choices([1, 2, 3])

        config = self.config.update_config(config)
        self.assertEqual(config.test.variable, 2)
        self.assertEqual(config.test.choice_variable, 1)
        # self.assertFalse(isinstance(config.test.choice_variable, Choices))
        self.assertTrue(hasattr(config.test, 'choice_variable2'))
        self.assertTrue(isinstance(config.test.choice_variable2, Choices))

