'''
Preprocessor for Foliant documentation authoring tool.
Generates documentation from PostgreSQL database structure,
'''


import re
import traceback
import psycopg2
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
    }

    # info about tables
    SQL_TABLES = '''SELECT
      st.relid,
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
        routine_body,
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

        self._host = self.options['host']
        self._port = self.options['port']
        self._dbname = self.options['dbname']
        self._user = self.options['user']
        self._password = self.options['password']
        self._schemas = self.options['schemas']

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

    def _to_md(self,
               tables: list,
               columns: list,
               fks: list,
               functions: list,
               triggers: list,
               parameters: list) -> str:
        result = ''
        if tables:
            result += '# Tables\n\n'
        for table in tables:
            name = table['relname']
            descr = table['description']
            result += f'## {name}\n\n{descr}\n\n'
            result += 'column | nullable | type | descr | fkey\n' +\
                      '------ | -------- | ---- | ----- | ----\n'
            fks_filtered = list(filter(lambda x: x['table_name'] ==
                                       table['relname'], fks))
            for col in columns:
                if col['table_name'] == table['relname']:
                    fkey = ''
                    for key in fks_filtered:
                        if key['column_name'] == col['column_name']:
                            fkey = key['foreign_table_name'] + \
                                '[' + key['foreign_column_name'] + ']'
                    result += col['column_name'] + ' | ' +\
                        col['is_nullable'] + ' | ' +\
                        col['data_type'] + ' | ' +\
                        col['description'] + ' | ' + fkey + '\n'
            result += '\n'

        if functions:
            result += '# Functions\n\n'
        for func in functions:
            name = func['routine_name']
            language = func['external_language']
            data_type = func['data_type']
            body = '    ' + func['routine_definition'].replace('\n', '\n    ')
            result += f'## {name}\n\n**Language**: {language}\n\n' +\
                      f'**Data Type**: {data_type}\n\n'
            params = list(filter(lambda x: x['specific_name'] ==
                                 func['specific_name'], parameters))
            if params:
                result += '**Parameters**:\n\n' +\
                          'name | type | mode | default\n' +\
                          '---- | ---- | ---- | -------\n'
                for param in params:
                    result += param['parameter_name'] + ' | ' +\
                        param['data_type'] + ' | ' +\
                        param['parameter_mode'] + ' | ' +\
                        param['parameter_default'] + '\n'
            result += f'\n{body}\n\n'
        result += '\n'
        if triggers:
            result += '# Triggers\n\n'
        for trigger in triggers:
            name = trigger['routine_name']
            body = '    ' + trigger['routine_definition'].replace('\n',
                                                                  '\n    ')
            result += f'## {name}\n\n{body}\n\n'

        return result

    def _to_uml(self, tables, columns, fks):
        result = '# Database Scheme\n\n<plantuml>\n    @startuml\n'
        for table in tables:
            name = table['relname']
            result += f'    object {name} {{\n'
            for col in columns:
                if col['table_name'] == table['relname']:
                    result += '    ' + col['column_name'] +\
                              ' [' + col['data_type'] + ']\n'
            result += '    }\n'

        for key in fks:
            result += '    ' + key['table_name'] + ' --|> ' +\
                      key['foreign_table_name'] + ' : ' + key['column_name'] +\
                      '\n'

        return result + '    @enduml\n</plantuml>'

    def _gen_docs(self,
                  schemas: list,
                  draw: bool) -> str:
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
        sql = self.SQL_TRIGGERS
        if schemas:
            sql += '\nAND routine_schema IN (%s);' % ','.join(schemas)
        self.logger.debug(f'SQL_TRIGGERS: \n{sql}')
        triggers = self._get_rows(sql)
        docs = self._to_md(tables,
                           columns,
                           fks,
                           functions,
                           triggers,
                           parameters)
        if draw:
            docs += '\n\n' + self._to_uml(tables, columns, fks)
        return docs

    def process_pgsqldoc_blocks(self, content: str) -> str:
        def _sub(block: str) -> str:
            if block.group('options'):
                tag_options = self.get_options(block.group('options'))
            else:
                tag_options = {}
            host = tag_options.get('host', self._host)
            port = tag_options.get('port', self._port)
            dbname = tag_options.get('dbname', self._dbname)
            user = tag_options.get('user', self._user)
            password = tag_options.get('password', self._password)
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
                self.logger.debug(f'Failed to connect: host={host} port={port}'
                                  f' dbname={dbname}, user={user} '
                                  f'password={password}.\n\n{info}')
                return ''
            if 'schemas' in tag_options:
                schemas = re.split(',\s*', tag_options['schemas'])
            else:
                schemas = self._schemas
            # add quotes to use in a query
            schemas = [f"'{i}'" for i in schemas]
            draw = tag_options.get('draw', self.options['draw'])
            return self._gen_docs(schemas, draw)
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
