import psycopg2
from abc import ABCMeta


class QueryBase(metaclass=ABCMeta):

    base_query = ''

    _filter_fields = {}
    # sort_fields = {}

    def __init__(self,
                 con: psycopg2.extensions.connection,
                 filters: dict = {}):
        self._con = con
        self._filters = self._get_filters(filters)

    def _get_filters(self, filters: dict):
        filter_str = ''
        for filter_ in filters:
            if filter_ not in self._filter_fields:
                continue
            if type(filters[filter_][0]) == str:
                values = [f"'{f}'" for f in filters[filter_]]
            values = ', '.join(values)
            field = self._filter_fields[filter_]
            filter_str += f'AND {field} in ({values})\n'
        return filter_str

    def _get_rows(self, sql) -> list:
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

    def run(self):
        sql = self.base_query.format(filters=self._filters)
        return self._get_rows(sql)


class TablesQuery(QueryBase):

    base_query = '''SELECT
      st.schemaname,
      st.relname,
      pd.description
    FROM pg_catalog.pg_statio_all_tables AS st
    LEFT JOIN pg_catalog.pg_description pd
           ON st.relid = pd.objoid
          AND pd.objsubid = 0
    WHERE 1 = 1
    {filters}'''

    _filter_fields = {'schema': 'schemaname'}


class ColumnsQuery(QueryBase):

    base_query = '''SELECT
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
          AND pd.objsubid = c.ordinal_position
    WHERE 1=1
    {filters}'''

    _filter_fields = {'schema': 'c.table_schema'}


class ForeignKeysQuery(QueryBase):

    base_query = '''SELECT
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
    WHERE constraint_type = 'FOREIGN KEY'
    {filters}'''


class FunctionsQuery(QueryBase):

    base_query = """SELECT
        routine_name,
        specific_name,
        data_type,
        routine_definition,
        -- routine_body,
        external_language
    FROM information_schema.routines
    WHERE data_type != 'trigger'
    {filters}"""

    _filter_fields = {'schema': 'routine_schema'}


class ParametersQuery(QueryBase):

    base_query = """SELECT
        specific_name,
        parameter_name,
        parameter_mode,
        data_type,
        parameter_default
    FROM information_schema.parameters
    WHERE 1=1
    {filters}"""

    _filter_fields = {'schema': 'specific_schema'}


class TriggersQuery(QueryBase):

    base_query = """SELECT
        routine_name,
        routine_definition
    FROM information_schema.routines
    WHERE data_type = 'trigger'
    {filters}"""

    _filter_fields = {'schema': 'routine_schema'}
