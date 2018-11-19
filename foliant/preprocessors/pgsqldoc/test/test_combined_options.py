from unittest import TestCase
from pgsqldoc.combined_options import CombinedOptions, yaml_to_dict_conversion


class TestCombinedOptions(TestCase):

    def test_init_priority(self):
        options = CombinedOptions({}, priority='config')
        self.assertEqual(options.priority, 'config')

        with self.assertRaises(ValueError):
            options = CombinedOptions({}, priority='wrong_priority')

    def test_get_combined_options(self):
        tag_options = {'a': 1, 'b': 2, 'c': 3}
        config_options = {'b': 4, 'c': 5, 'd': 6}

        options = CombinedOptions(config_options,
                                  tag_options)
        got = options.get_options()
        got_tag = options.get_options('tag')
        got_config = options.get_options('config')
        exptected_tag = {'b': 2, 'c': 3, 'a': 1, 'd': 6}
        exptected_config = {'b': 4, 'c': 5, 'a': 1, 'd': 6}
        self.assertEqual(got, exptected_tag)
        self.assertEqual(got_tag, got)
        self.assertEqual(got_config, exptected_config)

        with self.assertRaises(ValueError):
            got = options.get_options('wrong_priority')

    def test_get_item(self):
        tag_options = {'a': 1, 'b': 2, 'c': 3}
        config_options = {'b': 4, 'c': 5, 'd': 6}

        options = CombinedOptions(config_options,
                                  tag_options)
        self.assertEqual(options['a'], 1)
        self.assertEqual(options['b'], 2)
        self.assertEqual(options['c'], 3)
        self.assertEqual(options['d'], 6)

        with self.assertRaises(KeyError):
            options['wrong_key']

    def test_conversions(self):
        tag_options = {'a': 1}
        config_options = {'b': 2}

        options = CombinedOptions(config_options,
                                  tag_options,
                                  conversions={'c': lambda x: x})
        self.assertEqual(options['a'], 1)
        self.assertEqual(options['b'], 2)
        options = CombinedOptions(config_options,
                                  tag_options,
                                  conversions={'a': lambda x: 'a'})
        self.assertEqual(options['a'], 'a')
        self.assertEqual(options['b'], 2)

    def test_contains(self):
        tag_options = {'a': 1, 'b': 2, 'c': 3}
        config_options = {'b': 4, 'c': 5, 'd': 6}
        options = CombinedOptions(config_options,
                                  tag_options=tag_options)
        self.assertTrue('a' in options)
        self.assertTrue('b' in options)
        self.assertTrue('c' in options)
        self.assertTrue('d' in options)
        self.assertFalse('wrong_key' in options)


class TestYamlToDictConversion(TestCase):
    def test_dict_option(self):
        option = {'a': 1, 'b': 2}
        self.assertEqual(yaml_to_dict_conversion(option), option)

    def test_yaml_option(self):
        option = 'a: 1\nb: 2'
        expected = {'a': 1, 'b': 2}
        self.assertEqual(yaml_to_dict_conversion(option), expected)
