'''
Preprocessor for Foliant documentation authoring tool.
Generates documentation from PostgreSQL database structure,
'''

import traceback
import psycopg2
from jinja2 import Environment, FileSystemLoader
from pkg_resources import resource_filename
from foliant.preprocessors.base import BasePreprocessor
from .queries import (TablesQuery, ColumnsQuery, ForeignKeysQuery,
                      FunctionsQuery, ParametersQuery, TriggersQuery)
from .utils import copy_if_not_exists
from foliant.preprocessors.utils.combined_options import (CombinedOptions,
                                                          yaml_to_dict_convertor)
from foliant.utils import output
from copy import deepcopy


def collect_datasets(connection,
                     filters: dict) -> dict:

        result = {}

        tables = TablesQuery(connection, filters).run()
        columns = ColumnsQuery(connection, filters).run()
        fks = ForeignKeysQuery(connection, filters).run()

        # fill each table with columns and foreign keys
        result['tables'] = collect_tables(tables, columns, fks)

        functions = FunctionsQuery(connection, filters).run()
        parameters = ParametersQuery(connection, filters).run()

        # fill each function with its parameters

        result['functions'] = collect_functions(functions, parameters)

        result['triggers'] = TriggersQuery(connection, filters).run()
        return result


def collect_tables(tables: list,
                   columns: list,
                   fks: list) -> list:
    '''
    Parse table and column query results got from db and:

    - add 'columns' attribute to each table row with list of table columns;
    - add 'foreign_keys' attribute to each column with list of fks if it is a
      forign key column.

    returns transformed list of tables.
    '''

    result = deepcopy(tables)
    for table in result:
        # get columns for this table
        table_columns = list(filter(lambda x: x['table_name'] == table['relname'],
                                    columns))
        for col in table_columns:
            # get foreign keys for this column
            fks_fltr = list(filter(lambda x:
                                   x['table_name'] == table['relname'] and
                                   x['column_name'] == col['column_name'],
                                   fks))
            col['foreign_keys'] = fks_fltr
        table['columns'] = table_columns
    return result


def collect_functions(functions: list,
                      parameters: list) -> list:
    '''
    Parse function and parameter query results got from db and add 'parameters'
    key to each function filled with its parameters
    '''

    result = deepcopy(functions)
    for func in result:
        # get parameters for this function
        function_params = list(filter(lambda x: x['specific_name'] ==
                                      func['specific_name'],
                                      parameters))
        func['parameters'] = function_params
    return result


class Preprocessor(BasePreprocessor):
    tags = ('pgsqldoc',)

    defaults = {
        'draw': False,
        'host': 'localhost',
        'port': '5432',
        'dbname': 'postgres',
        'user': 'postgres',
        'password': '',
        'filters': {},
        'doc_template': 'pgsqldoc.j2',
        'scheme_template': 'scheme.j2'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = self.logger.getChild('pgsqldoc')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

        self._env = \
            Environment(loader=FileSystemLoader(str(self.project_path)))

    def _to_md(self,
               data: dict,
               doc_template: str) -> str:
        try:
            template = self._env.get_template(doc_template)
            result = template.render(tables=data['tables'],
                                     functions=data['functions'],
                                     triggers=data['triggers'])
        except Exception as e:
            output(f'\nFailed to render doc template {doc_template}:', self.quiet)
            info = traceback.format_exc()
            self.logger.debug(f'Failed to render doc template:\n\n{info}')
            return ''
        return result

    def _to_diag(self,
                 data: dict,
                 scheme_template: str) -> str:
        try:
            template = self._env.get_template(scheme_template)
            result = template.render(tables=data['tables'])
        except Exception as e:
            info = traceback.format_exc()
            self.logger.debug(f'Failed to render scheme template:\n\n{info}')
            return ''
        return result

    def _gen_docs(self,
                  options: CombinedOptions) -> str:
        data = collect_datasets(self._con, options['filters'])
        docs = self._to_md(data, options['doc_template'])
        if options['draw']:
            docs += '\n\n' + self._to_diag(data,
                                           options['scheme_template'])
        return docs

    def _connect(self, options: CombinedOptions):
        """
        Connect to PostgreSQL database using parameters from options.
        Save connection object into self._con.

        options(CombinedOptions) — CombinedOptions object with options from tag
                                   and config.
        """
        try:
            self._con = None
            self.logger.debug(f"Trying to connect: host={options['host']} port={options['port']}"
                              f" dbname={options['dbname']}, user={options['user']} "
                              f"password={options['password']}.")
            self._con = psycopg2.connect(f"host='{options['host']}' "
                                         f"port='{options['port']}' "
                                         f"dbname='{options['dbname']}' "
                                         f"user='{options['user']}'"
                                         f"password='{options['password']}'")
        except psycopg2.OperationalError:
            info = traceback.format_exc()
            output(f"\nFailed to connect to host {options['host']}. "
                   'Documentation was not generated', self.quiet)
            self.logger.debug(f'Failed to connect: host={options["host"]}'
                              f' port={options["port"]}'
                              f' dbname={options["dbname"]} '
                              f'user={options["user"]} '
                              f'password={options["password"]}.\n\n{info}')
            raise psycopg2.OperationalError

    def _create_default_templates(self, options: CombinedOptions):
        """
        Copy default templates to project dir if their names in options are
        same as default.
        """

        if options.is_default('doc_template'):
            source = self.project_path / options['doc_template']
            to_copy = resource_filename(__name__,
                                        f"templates/{options.defaults['doc_template']}")
            copy_if_not_exists(source, to_copy)

        if options.is_default('scheme_template'):
            source = self.project_path / options['scheme_template']
            to_copy = resource_filename(__name__,
                                        f"templates/{options.defaults['scheme_template']}")
            copy_if_not_exists(source, to_copy)

    def process_pgsqldoc_blocks(self, content: str) -> str:
        def _sub(block) -> str:
            tag_options = self.get_options(block.group('options'))
            options = CombinedOptions({'config': self.options,
                                       'tag': tag_options},
                                      priority='tag',
                                      convertors={'filters': yaml_to_dict_convertor},
                                      defaults=self.defaults)
            self._connect(options)
            if not self._con:
                return ''

            self._create_default_templates(options)
            return self._gen_docs(options)
        return self.pattern.sub(_sub, content)

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            self.logger.debug(f'Processing Markdown file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                content = markdown_file.read()

            processed_content = self.process_pgsqldoc_blocks(content)

            with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                markdown_file.write(processed_content)

        self.logger.info('Preprocessor applied')
