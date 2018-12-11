import yaml


class CombinedOptions:
    '''Helper class for combining tag and config options'''

    def __init__(self,
                 config_options: dict,
                 tag_options: dict = {},  # match object
                 priority: str = 'tag',
                 conversions: dict = {},
                 defaults: dict = {}):
        self._config_options = dict(config_options)
        self._tag_options = dict(tag_options)
        if priority in ('tag', 'config'):
            self.priority = priority
        else:
            raise ValueError('Priority must be one of: tag, config.'
                             f' Value received: {priority}')
        self._conversions = conversions
        self.defaults = defaults

    @property
    def tag(self):
        return self._tag_options

    @property
    def config(self):
        return self._config_options

    def get_options(self, priority: str or None = None) -> dict:
        '''
        Return options dict with options combined from config and tag with
        priority according to priority param or self.priority if param is not
        given.

        priority (str) — override self.priority for choosing overlapping
                         options. Must be one of: 'tag', 'config'.
        '''
        if not priority:
            priority_choosen = self.priority
        elif priority not in ('tag', 'config'):
            raise ValueError('Priority must be one of: tag, config.'
                             f' Value received: {priority}')
        else:
            priority_choosen = priority
        if priority_choosen == 'tag':
            result = {**self._config_options, **self._tag_options}
        elif priority_choosen == 'config':
            result = {**self._tag_options, **self._config_options}
        for key in self._conversions:
            if key in result:
                result[key] = self._conversions[key](result[key])
        return result

    def is_default(self, option):
        '''return True if option value is same as default'''
        if option in self.defaults:
            return self.get_options()[option] == self.defaults[option]
        return False

    def __getitem__(self, ind: str):
        return self.get_options()[ind]

    def __contains__(self, ind: str):
        return ind in self._tag_options or ind in self._config_options


def yaml_to_dict_conversion(option: str or dict):
    '''convert yaml string or dict to dict'''

    if type(option) is dict:
        return option
    elif type(option) is str:
        return yaml.load(option)
