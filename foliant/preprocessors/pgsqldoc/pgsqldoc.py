'''
Preprocessor for Foliant documentation authoring tool.
Generates documentation from PostgreSQL database structure,
'''


import re
import os
import traceback
import psycopg2
from shutil import copyfile
from jinja2 import Environment, FileSystemLoader
from pkg_resources import resource_string, resource_filename
from foliant.preprocessors.base import BasePreprocessor


class Preprocessor(BasePreprocessor):
    tags = ('pgsqldoc',)

    defaults = {
        'draw': False,
        'host': 'localhost',
        'port': '5432',
        'dbname': 'postgres',
        'user': 'postgres',
        'password': '',
        'schemas': [],
        'doc_template': 'pgsqldoc.j2',
        'scheme_template': 'scheme.j2'
    }

    # info about tables
    SQL_TABLES = '''SELECT
      st.schemaname,
      st.relname,
      pd.description
    FROM pg_catalog.pg_statio_all_tables AS st
    LEFT JOIN pg_catalog.pg_description pd
           ON st.relid = pd.objoid
          AND pd.objsubid = 0'''

    # info about columns of all tables
    SQL_COLUMNS = '''SELECT
      c.table_name,
      c.ordinal_position,
      c.column_name,
      c.is_nullable,
      c.data_type,
      c.column_default,
      c.character_maximum_length,
      c.numeric_precision,
      pd.description
    FROM information_schema.columns c
    JOIN pg_catalog.pg_statio_all_tables st
      ON st.schemaname = c.table_schema
     AND st.relname = c.table_name
    LEFT JOIN pg_catalog.pg_description pd
           ON pd.objoid = st.relid
          AND pd.objsubid = c.ordinal_position'''

    # all foreign keys
    SQL_FKS = '''SELECT
        tc.table_schema,
        tc.constraint_name,
        tc.table_name,
        kcu.column_name,
        ccu.table_schema AS foreign_table_schema,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM
        information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
    WHERE constraint_type = 'FOREIGN KEY';'''

    # all stored functions
    SQL_FUNCTIONS = """SELECT
        routine_name,
        specific_name,
        data_type,
        routine_definition,
        -- routine_body,
        external_language
    FROM information_schema.routines
    WHERE data_type != 'trigger'"""

    # all functions parameters
    SQL_PARAMETERS = """SELECT
        specific_name,
        parameter_name,
        parameter_mode,
        data_type,
        parameter_default
    FROM information_schema.parameters
    """

    SQL_TRIGGERS = """SELECT
        routine_name,
        routine_definition
    FROM information_schema.routines
    WHERE data_type = 'trigger'"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = self.logger.getChild('pgsqldoc')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

        self._env = \
            Environment(loader=FileSystemLoader(str(self.project_path)))

    def _get_rows(self, sql: str) -> list:
        """Run query from sql param and return a list of dicts key=column name,
        value = field value"""
        cur = self._con.cursor()
        cur.execute(sql)
        result = []
        keys = tuple((d[0] for d in cur.description))
        for row in cur.fetchall():
            row_dict = {}
            for i in range(len(keys)):
                row_dict[keys[i]] = row[i] or ''
            result.append(row_dict)
        return result

    def _collect_datasets(self,
                          schemas: list,
                          draw: bool) -> dict:
        result = {}
        sql = self.SQL_TABLES
        if schemas:
            sql += '\nWHERE schemaname IN (%s);' % ','.join(schemas)
        self.logger.debug(f'SQL_TABLES: \n{sql}')
        tables = self._get_rows(sql)
        sql = self.SQL_COLUMNS
        if schemas:
            sql += '\nWHERE st.schemaname IN (%s);' % ','.join(schemas)
        self.logger.debug(f'SQL_COLUMNS: \n{sql}')
        columns = self._get_rows(sql)
        fks = self._get_rows(self.SQL_FKS)

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

        sql = self.SQL_FUNCTIONS
        if schemas:
            sql += '\nAND routine_schema IN (%s);' % ','.join(schemas)
        self.logger.debug(f'SQL_FUNCTIONS: \n{sql}')
        functions = self._get_rows(sql)
        sql = self.SQL_PARAMETERS
        if schemas:
            sql += '\nWHERE specific_schema IN (%s);' % ','.join(schemas)
        self.logger.debug(f'SQL_PARAMETERS: \n{sql}')
        parameters = self._get_rows(sql)

        # fill each function with its parameters
        for func in functions:
            params_fltr = list(filter(lambda x: x['specific_name'] ==
                                      func['specific_name'],
                                      parameters))
            func['parameters'] = params_fltr

        result['functions'] = functions

        sql = self.SQL_TRIGGERS
        if schemas:
            sql += '\nAND routine_schema IN (%s);' % ','.join(schemas)
        self.logger.debug(f'SQL_TRIGGERS: \n{sql}')
        triggers = self._get_rows(sql)
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
                  schemas: list,
                  draw: bool,
                  doc_template: str,
                  scheme_template: str) -> str:
        # add quotes to use in a query
        schemas_cl = [f"'{i}'" for i in schemas]

        data = self._collect_datasets(schemas_cl, draw)
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
            if 'schemas' in tag_options:
                schemas = re.split(',\s*', tag_options['schemas'])
            else:
                schemas = self.options['schemas']
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
            return self._gen_docs(schemas, draw, doc_template, scheme_template)
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
