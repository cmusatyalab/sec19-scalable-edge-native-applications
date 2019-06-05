from __future__ import (absolute_import, division, print_function,
                        with_statement)
from schema import models

import os
import sys
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.append(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..'))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# custom db url settings
config.set_main_option('sqlalchemy.url', os.getenv('DB_URI'))

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# added to exclude certain tables from alembic
def get_exclude_tables_from_config(config_):
    tables_ = config_.get('table_name_regex', None)
    if tables_ is not None:
        tables = tables_.split(' ')
    print(tables)
    return tables


exclude_tables = get_exclude_tables_from_config(
    config.get_section('alembic:exclude'))


def should_exclude_table(table_name, exclude_tables):
    for exclude_table_pattern in exclude_tables:
        if re.match(exclude_table_pattern, table_name):
            return True
    return False


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and should_exclude_table(name, exclude_tables):
        return False
    else:
        return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        include_object=include_object
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
