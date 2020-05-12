#TODO remove unused imports
"""
Afterglow Core: field-cals resource
"""

from __future__ import absolute_import, division, print_function

from sqlalchemy import Column, Float, Integer, String
from flask import request

from .. import app, auth, json_response
from ..models.field_cal import FieldCal
from ..errors import MissingFieldError
from ..errors.field_cal import UnknownFieldCalError, DuplicateFieldCalError
from .data_files import Base, get_data_file_db

try:
    # noinspection PyUnresolvedReferences
    from alembic import config as alembic_config, context as alembic_context
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext
except ImportError:
    ScriptDirectory = EnvironmentContext = None
    alembic_config = alembic_context = None


__all__ = ['get_field_cal']


class SqlaFieldCal(Base):
    __tablename__ = 'field_cals'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(1024), unique=True, nullable=False, index=True)
    catalog_sources = Column(String)
    catalogs = Column(String)
    custom_filter_lookup = Column(String)
    source_inclusion_percent = Column(Float)
    min_snr = Column(Float, server_default='0')
    max_snr = Column(Float, server_default='0')
    source_match_tol = Column(Float)


def get_field_cal(user_id, id_or_name):
    """
    Return field cal with the given ID or name

    :param int | None user_id: current user ID (None if user auth is disabled)
    :param int | str id_or_name: field cal ID (integer) or name

    :return: serialized field cal object
    :rtype: FieldCal
    """
    adb = get_data_file_db(user_id)

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


