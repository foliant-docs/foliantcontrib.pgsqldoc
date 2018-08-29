# PostgreSQL Docs Generator for Foliant

This preprocessor generates simple documentation of a PostgreSQL database based on its structure. It uses [Jinja2](http://jinja.pocoo.org/) templating engine for customizing the layout and [PlantUML](http://plantuml.com/) for drawing the database scheme.

## Installation

```bash
$ pip install foliantcontrib.pgsqldoc
```

## Config

To enable the preprocessor, add `pgsqldoc` to `preprocessors` section in the project config:

```yaml
preprocessors:
    - pgsqldoc
```

The preprocessor has a number of options:

```yaml
preprocessors:
    - pgsqldoc:
        host: localhost
        port: 5432
        dbname: postgres
        user: postgres
        password: ''
        draw: false
        filters:
            ...
        doc_template: pgsqldoc.j2
        scheme_template: scheme.j2
```

`host`
:   PostgreSQL database host address. Default: `localhost`

`port`
:   PostgreSQL database port. Default: `5432`

`dbname`
:   PostgreSQL database name. Default: `postgres`

`user`
:   PostgreSQL user name. Default: `postgres`

`passwrod`
:   PostgreSQL user password.

`draw`
:   If this parameter is `true` — preprocessor would generate scheme of the database and add it to the end of the document. Default: `false`

`filters`
:   SQL-like operators for filtering the results. More info in the **Filters** section.

`doc_template`
:   Path to jinja-template for documentation. Path is relative to the project directory. Default: `pgsqldoc.j2`

`scheme_template`
:   Path to jinja-template for scheme. Path is relative to the project directory. Default: `scheme.j2`

## Usage

Add a `<<pgsqldoc></pgsqldoc>` tag at the position in the document where the generated documentation of a PostgreSQL database should be inserted:

```markdown
# Introduction

This document contains the most awesome automatically generated documentation of our marvellous database.

<<pgsqldoc></pgsqldoc>
```

Each time the preprocessor encounters the tag `<<pgsqldoc></pgsqldoc>` it inserts the whole generated documentation text instead of it. The connection parameters are taken from the config-file.

You can also specify some parameters (or all of them) in the tag options:

```markdown
# Introduction

Introduction text for database documentation.

<pgsqldoc draw="true"
          host="11.51.126.8"
          port="5432"
          dbname="mydb"
          user="scott"
          password="tiger">
</pgsqldoc>
```

Tag parameters have the highest priority.

This way you can have documentation for several different databases in one foliant project (even in one md-file if you like it so).

## Filters

You can add filters to exclude some tables from the documentation. Pgsqldocs supports several SQL-like filtering operators and a determined list of filtering fields.

You can switch on filters either in foliant.yml file like this:

```yaml
preprocessors:
  - pgsqldoc:
    filters:
      eq:
        schema: public
      regex:
        table_name: 'main_.+'
```

or in tag options using the same yaml-syntax:

```markdown

<pgsqldoc filters="
eq:
    schema: public
  regex:
    table_name: 'main_.+'">
</pgsqldoc>

```

List of currently supported operators:

operator | SQL equivalent | description | value
-------- | -------------- | ----------- | -----
`eq` | `=` | equals | literal
`not_eq` | `!=` | does not equal | literal
`in` | `IN` | contains | list
`not_in` | `NOT IN` | does not contain | list
`regex` | `~` | matches regular expression | literal
`not_regex` | `!~` | does not match regular expression | literal

List of currently supported filtering fields:

field | description
----- | -----------
schema | filter by PostgreSQL database schema
table_name | filter by database table names

The syntax for using filters in configuration files is following:

```yaml
filters:
  <operator>:
    <field>: value
```

If `value` should be list like for `in` operator, use YAML-lists instead:

```yaml
filters:
  in:
    schema:
      - public
      - corp
```

## About Templates

The structure of generated documentation is defined by jinja-templates. You can choose what elements will appear in the documentation, change their positions, add constant text, change layouts and more. Check the [Jinja documentation](http://jinja.pocoo.org/docs/2.10/templates/) for info on all cool things you can do with templates.

If you don't specify path to templates in the config-file and tag-options pgsqldoc will use default paths:

- `<Project_path>/pgsqldoc.j2` for documentation template;
- `<Project_path>/scheme.j2` for database scheme source template.

If pgsqldoc can't find these templates in the project dir it will generate default templates and put them there.

So if you accidentally mess things up while experimenting with templates you can always delete your templates and run preprocessor — the default ones will appear in the project dir. (But only if the templates are not specified in config-file or their names are the same as defaults).

One more useful thing about default templates is that you can find a detailed description of the source data they get from pgsqldoc in the beginning of the template.
