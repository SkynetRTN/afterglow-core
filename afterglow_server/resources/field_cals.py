"""
Afterglow Access Server: field-cals resource
"""

from __future__ import absolute_import, division, print_function

import os
import sqlite3
from threading import Lock

from sqlalchemy import Column, Float, Integer, String, create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# noinspection PyProtectedMember
from sqlalchemy.engine import Engine
from flask import request

from ..data_structures import FieldCal
from ..auth import auth_required, current_user
from .. import app, errors, json_response, url_prefix
from .data_files import CannotCreateDataFileDirError, get_root

try:
    # noinspection PyUnresolvedReferences
    from alembic import config as alembic_config, context as alembic_context
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext
except ImportError:
    ScriptDirectory = EnvironmentContext = None
    alembic_config = alembic_context = None


__all__ = [
    'DuplicateFieldCalError', 'UnknownFieldCalError',
    'get_field_cal', 'get_field_cal_db',
]


class UnknownFieldCalError(errors.AfterglowError):
    """
    Unknown field calibration

    Extra attributes::
        id: requested field cal ID
    """
    code = 404
    subcode = 4000
    message = 'Unknown field cal'


class DuplicateFieldCalError(errors.AfterglowError):
    """
    Field cal with this name already exists

    Extra attributes::
        name: field cal name
    """
    subcode = 4001
    message = 'Duplicate field cal name'


Base = declarative_base()


class SqlaFieldCal(Base):
    __tablename__ = 'field_cals'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, unique=True, nullable=False, index=True)
    catalog_sources = Column(String)
    catalogs = Column(String)
    custom_filter_lookup = Column(String)
    source_inclusion_percent = Column(Float)
    min_snr = Column(Float, server_default='0')
    max_snr = Column(Float, server_default='0')
    source_match_tol = Column(Float)


# SQLA database engine
field_cals_engine = {}
field_cals_engine_lock = Lock()


def get_field_cal_db(user_id):
    """
    Initialize the given user's data file storage directory and field cal
    database as needed and return the database object; thread-safe

    :return: SQLAlchemy session object
    :rtype: sqlalchemy.orm.session.Session
    """
    try:
        root = get_root(user_id)

        # Make sure the user's data directory exists
        if os.path.isfile(root):
            os.remove(root)
        if not os.path.isdir(root):
            os.makedirs(root)

        with field_cals_engine_lock:
            try:
                # Get engine from cache
                engine = field_cals_engine[root]
            except KeyError:
                # Engine does not exist, create it
                @event.listens_for(Engine, 'connect')
                def set_sqlite_pragma(dbapi_connection, _rec):
                    if isinstance(dbapi_connection, sqlite3.Connection):
                        cursor = dbapi_connection.cursor()
                        cursor.execute('PRAGMA journal_mode=WAL')
                        cursor.close()
                engine = field_cals_engine[root] = create_engine(
                    'sqlite:///{}'.format(os.path.join(root, 'field_cals.db')),
                    connect_args={'check_same_thread': False,
                                  'isolation_level': None},
                )

                # Create field_cals table
                if alembic_config is None:
                    # Alembic not available, create table from SQLA metadata
                    Base.metadata.create_all(bind=engine)
                else:
                    # Create/upgrade table via Alembic
                    cfg = alembic_config.Config()
                    cfg.set_main_option(
                        'script_location',
                        os.path.abspath(os.path.join(
                            __file__, '..', '..', 'db_migration', 'field_cals'))
                    )
                    script = ScriptDirectory.from_config(cfg)

                    def upgrade(rev, _):
                        # noinspection PyProtectedMember
                        return script._upgrade_revs('head', rev)

                    with EnvironmentContext(
                                cfg,
                                script,
                                fn=upgrade,
                                as_sql=False,
                                starting_rev=None,
                                destination_rev='head',
                                tag=None,
                            ), engine.connect() as connection:
                        alembic_context.configure(connection=connection)

                        with alembic_context.begin_transaction():
                            alembic_context.run_migrations()

            return scoped_session(sessionmaker(bind=engine))()

    except Exception as e:
        raise CannotCreateDataFileDirError(
            reason=e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e))


def get_field_cal(user_id, id_or_name):
    """
    Return field cal with the given ID or name

    :param int | None user_id: current user ID (None if user auth is disabled)
    :param int | str id_or_name: field cal ID (integer) or name

    :return: serialized field cal object
    :rtype: FieldCal
    """
    adb = get_field_cal_db(user_id)
    try:
        field_cal = adb.query(SqlaFieldCal).get(int(id_or_name))
    except ValueError:
        field_cal = None
    if field_cal is None:
        # Try getting by name
        field_cal = adb.query(SqlaFieldCal).filter(
            SqlaFieldCal.name == id_or_name).one_or_none()
    if field_cal is None:
        raise UnknownFieldCalError(id=id_or_name)
    return FieldCal.from_db(field_cal)


resource_prefix = url_prefix + 'field-cals/'


@app.route(resource_prefix[:-1], methods=['GET', 'POST'])
@app.route(resource_prefix + '<id_or_name>', methods=['GET', 'PUT', 'DELETE'])
@auth_required('user')
def field_cals(id_or_name=None):
    """
    Return, create, update, or delete field cal(s)

    GET /field-cals
        - return a list of all user's field cals

    GET /field-cals/[id or name]
        - return a single field cal with the given ID or name

    POST /field-cals?name=...
        - create field cal with the given name and parameters

    PUT /field-cals/[id or name]?...
        - update field cal parameters

    DELETE /field-cals/[id or name]
        - delete the given field cal

    :param str id_or_name: field cal ID (integer) or name

    :return:
        GET: JSON response containing either a list of serialized field cals
            when no ID/name supplied or a single field cal otherwise
        POST, PUT: JSON-serialized field cal
        DELETE: empty response
    :rtype: flask.Response | str
    """
    adb = get_field_cal_db(current_user.id)
    if id_or_name is not None:
        # When getting, updating, or deleting a field cal, check that it
        # exists
        try:
            field_cal = adb.query(SqlaFieldCal).get(int(id_or_name))
        except ValueError:
            field_cal = None
        if field_cal is None:
            # Try getting by name
            field_cal = adb.query(SqlaFieldCal).filter(
                SqlaFieldCal.name == id_or_name).one_or_none()
        if field_cal is None:
            raise UnknownFieldCalError(id=id_or_name)
    else:
        field_cal = None

    if request.method == 'GET':
        if id_or_name is None:
            # List all field cals
            return json_response(
                [FieldCal.from_db(field_cal)
                 for field_cal in adb.query(SqlaFieldCal)])

        # Return specific field cal resource
        return json_response(FieldCal.from_db(field_cal))

    if request.method == 'POST':
        # Create field cal
        if not request.args.get('name'):
            raise errors.MissingFieldError(field='name')
        if adb.query(SqlaFieldCal).filter(
                SqlaFieldCal.name == request.args['name']).count():
            raise DuplicateFieldCalError(name=request.args['name'])
        try:
            field_cal = SqlaFieldCal(**request.args.to_dict())
            adb.add(field_cal)
            adb.flush()
            res = FieldCal.from_db(field_cal)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response(res, 201)

    if request.method == 'PUT':
        # Update field cal
        for key, val in request.args.items():
            if key == 'id':
                # Don't allow changing field cal ID
                continue
            if key == 'name' and val != field_cal.name and adb.query(
                    SqlaFieldCal).filter(SqlaFieldCal.name == val).count():
                raise DuplicateFieldCalError(name=val)
            setattr(field_cal, key, val)
        try:
            res = FieldCal.from_db(field_cal)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response(res)

    if request.method == 'DELETE':
        # Delete field cal
        try:
            adb.query(SqlaFieldCal).filter(
                SqlaFieldCal.id == field_cal.id).delete()
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response()
