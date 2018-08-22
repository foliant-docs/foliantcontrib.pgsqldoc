# PostgreSQL Automatic Documentation Preprocessor for Foliant

This preprocessor generates simple documentation of PostgreSQL databases based on the structure and the comments. It uses [PlantUML](http://plantuml.com/) to draw the database scheme.


## Installation

```bash
$ pip install foliantcontrib.pgsqldoc
```

## Config

To enable the preprocessor, add `pgsqldoc` to `preprocessors` section in the project config:

```yaml
preprocessors:
    - pgsql
```

The preprocessor has a number of options:

```yaml
preprocessors:
    - pgsql:
        draw: false
        host: localhost
        port: 5432
        dbname: postgres
        user: postgres
        password: ''
        schemas:
            - 'public'
            - ...
```

`draw`
:   If this parameter is `true` — preprocessor would generate the scheme of the database and add it to the end of the document. Default: `false`

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

`schemas`
:   List of PostgreSQL database schema names to include in the documentation.

## Usage

Add a `<<pgsqldoc></pgsqldoc>` tag at the position in the document where the generated documentation of a PostgreSQL database should be inserted:

```markdown
# Introduction

This document contains the most awesome automatically generated documentation of our marvellous database.

<<pgsqldoc></pgsqldoc>
```

Each time the preprocessor encounters the tag `<<pgsqldoc></pgsqldoc>` it inserts the whole generated document instead of it. The connection parameters are taken from config.

You can also specify each parameter in the tag options:

```markdown
# Introduction

Introduction text for database documentation.

<pgsqldoc draw="true"
          host="11.51.126.8"
          port="5432"
          dbname="mydb"
          user="john"
          password="tiger"
          schemas="public, corp">
</pgsqldoc>
```

Tag parameters have the highest priority.

This way you can have documentation for several different databases in one foliant project (even in one md-file if you like it so).

## Generated Document Structure

Generated documentation consists of four sections:

**Tables** — all tables from the database and their columns. Comments act as description and are added for both tables and columns.

**Functions** — all stored functions from the database, their source code and information about parameters. Functions description is currently not supported.

**Triggers** — all triggers and their source code.

**Database Scheme** — scheme of the database drawn by PlantUML.