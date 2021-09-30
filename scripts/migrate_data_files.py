#!/usr/bin/env python

"""
Migrate one or more user data file directories to the latest database version
"""

import argparse
import os
import sys
from glob import glob

from sqlalchemy import create_engine
from alembic import config as alembic_config, context as alembic_context
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'dirs', metavar='DIRS',
        help='path to user data file director(ies) to migrate; '
             'may include wildcards')
    args = parser.parse_args()

    cfg = alembic_config.Config()
    cfg.set_main_option(
        'script_location',
        os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'afterglow_core',
            'db_migration', 'data_files'))
    )
    script = ScriptDirectory.from_config(cfg)

    for root in glob(args.dirs):
        if not os.listdir(root):
            continue
        db_path = os.path.join(root, 'data_files.db')
        if not os.path.isfile(db_path):
            continue

        print('Migrating', root, '...', end=' ', file=sys.stderr)
        db_url = 'sqlite:///{}'.format(db_path)
        engine = create_engine(
            db_url,
            connect_args={'check_same_thread': False,
                          'isolation_level': None},
        )

        try:
            # noinspection PyProtectedMember
            with EnvironmentContext(
                    cfg, script,
                    fn=lambda rev, _: script._upgrade_revs('head', rev),
                    as_sql=False, starting_rev=None, destination_rev='head',
                    tag=None,
            ), engine.connect() as connection:
                alembic_context.configure(connection=connection)
                with alembic_context.begin_transaction():
                    alembic_context.run_migrations()
        except Exception as e:
            print(e, file=sys.stderr)
        else:
            print('OK', file=sys.stderr)
        finally:
            engine.dispose()
