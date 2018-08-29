'''
Preprocessor for Foliant documentation authoring tool.
Generates documentation from PostgreSQL database structure,
'''


import re
import os
import traceback
import psycopg2
import yaml
from shutil import copyfile
from jinja2 import Environment, FileSystemLoader
from pkg_resources import resource_filename
from foliant.preprocessors.base import BasePreprocessor
from .queries import (TablesQuery, ColumnsQuery, ForeignKeysQuery,
                      FunctionsQuery, ParametersQuery, TriggersQuery,
                      SCHEMA, TABLE_NAME)


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

    def _collect_datasets(self,
                          filters: dict,
                          draw: bool) -> dict:

        result = {}

        tables = TablesQuery(self._con, filters).run()
        columns = ColumnsQuery(self._con, filters).run()
        fks = ForeignKeysQuery(self._con, filters).run()

        # fill each table with columns and foreign keys
        for table in tables:
            columns_fltr = list(filter(lambda x:
                                       x['table_name'] == table['relname'],
                                       columns))
            for col in columns_fltr:
                fks_fltr = list(filter(lambda x:
                                       x['table_name'] == table['relname'] and
                                       x['column_name'] == col['column_name'],
                                       fks))
                col['foreign_keys'] = fks_fltr
            table['columns'] = columns_fltr

        result['tables'] = tables

        functions = FunctionsQuery(self._con, filters).run()
        parameters = ParametersQuery(self._con, filters).run()

        # fill each function with its parameters
        for func in functions:
            params_fltr = list(filter(lambda x: x['specific_name'] ==
                                      func['specific_name'],
                                      parameters))
            func['parameters'] = params_fltr

        result['functions'] = functions

        triggers = TriggersQuery(self._con, filters).run()
        result['triggers'] = triggers
        return result

    def _to_md(self,
               data: dict,
               doc_template: str) -> str:
        try:
            template = self._env.get_template(doc_template)
            result = template.render(tables=data['tables'],
                                     functions=data['functions'],
                                     triggers=data['triggers'])
        except Exception as e:
            print(f'\nFailed to render doc template {doc_template}:', e)
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
                  filters: dict,
                  draw: bool,
                  doc_template: str,
                  scheme_template: str) -> str:
        data = self._collect_datasets(filters, draw)
        docs = self._to_md(data, doc_template)
        if draw:
            docs += '\n\n' + self._to_diag(data, scheme_template)
        return docs

    def process_pgsqldoc_blocks(self, content: str) -> str:
        def _sub(block: str) -> str:
            if block.group('options'):
                tag_options = self.get_options(block.group('options'))
            else:
                tag_options = {}
            host = tag_options.get('host', self.options['host'])
            port = tag_options.get('port', self.options['port'])
            dbname = tag_options.get('dbname', self.options['dbname'])
            user = tag_options.get('user', self.options['user'])
            password = tag_options.get('password', self.options['password'])
            self._con = None
            try:
                self.logger.debug(f'Trying to connect: host={host} port={port}'
                                  f' dbname={dbname}, user={user} '
                                  f'password={password}.')
                self._con = psycopg2.connect(f"host='{host}' "
                                             f"port='{port}' "
                                             f"dbname='{dbname}' "
                                             f"user='{user}'"
                                             f"password='{password}'")
            except psycopg2.OperationalError as e:
                info = traceback.format_exc()
                print(f'\nFailed to connect to host {host}. '
                      'Documentation was not generated')
                self.logger.debug(f'Failed to connect: host={host} port={port}'
                                  f' dbname={dbname}, user={user} '
                                  f'password={password}.\n\n{info}')
                return ''
            if 'filters' in tag_options:
                filters = yaml.load(tag_options['filters'])
            else:
                filters = self.options['filters']

            draw = tag_options.get('draw', self.options['draw'])

            doc_template = tag_options.get('doc_template',
                                           self.options['doc_template'])
            scheme_template = tag_options.get('scheme_template',
                                              self.options['scheme_template'])
            if doc_template == self.defaults['doc_template'] and\
                    not os.path.exists(self.project_path / doc_template):
                copyfile(resource_filename(__name__, 'templates/pgsqldoc.j2'),
                         self.project_path / doc_template)
            if scheme_template == self.defaults['scheme_template'] and\
                    not os.path.exists(self.project_path / scheme_template):
                copyfile(resource_filename(__name__, 'templates/scheme.j2'),
                         self.project_path / scheme_template)
            return self._gen_docs(filters, draw, doc_template, scheme_template)
        return self.pattern.sub(_sub, content)

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            self.logger.debug(f'Processing Markdown file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                content = markdown_file.read()

            with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                markdown_file.write(self.process_pgsqldoc_blocks(content))

        self.logger.info('Preprocessor applied')
