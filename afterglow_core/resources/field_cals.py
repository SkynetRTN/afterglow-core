"""
Afterglow Core: photometric field calibration prescriptions resource
"""

import os
from typing import List as TList, Optional, Union

from sqlalchemy import Column, Float, Integer, String, UniqueConstraint
from alembic import config as alembic_config, context as alembic_context
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext

from ..database import db
from ..models import FieldCal
from ..errors.field_cal import DuplicateFieldCalError, UnknownFieldCalError
from .base import JSONType


__all__ = [
    'init_field_cals',
    'query_field_cals', 'get_field_cal', 'create_field_cal', 'update_field_cal', 'delete_field_cal',
]


class DbFieldCal(db.Model):
    __tablename__ = 'field_cals'
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='_user_id_name_uc'),
    )

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, index=True)
    name = Column(String(1023), nullable=False, index=True)
    catalog_sources = Column(JSONType)
    catalogs = Column(JSONType)
    custom_filter_lookup = Column(JSONType)
    source_inclusion_percent = Column(Float)
    min_snr = Column(Float, server_default='0')
    max_snr = Column(Float, server_default='0')
    source_match_tol = Column(Float)
    variable_check_tol = Column(Float, server_default='5')
    max_star_rms = Column(Float, server_default='0')
    max_stars = Column(Integer, server_default='0')


def init_field_cals() -> None:
    """
    Initialize data file database tables
    """
    # Create/upgrade field cal tables via Alembic
    cfg = alembic_config.Config()
    cfg.set_main_option(
        'script_location', os.path.abspath(os.path.join(__file__, '..', '..', 'db_migration', 'field_cals'))
    )
    script = ScriptDirectory.from_config(cfg)
    with EnvironmentContext(
            cfg, script, fn=lambda rev, _: script._upgrade_revs('head', rev), as_sql=False,
            starting_rev=None, destination_rev='head', tag=None), db.engine.connect() as connection:
        alembic_context.configure(connection=connection, version_table='alembic_version_field_cals')

        with alembic_context.begin_transaction():
            alembic_context.run_migrations()


def query_field_cals(user_id: Optional[int]) -> TList[FieldCal]:
    """
    Return all user's field cals

    :param user_id: current user ID (None if user auth is disabled)

    :return: list of field cal objects
    """
    try:
        return [FieldCal(db_field_cal) for db_field_cal in DbFieldCal.query.filter_by(user_id=user_id)]
    except Exception:
        db.session.rollback()
        raise


def get_field_cal(user_id: Optional[int],
                  id_or_name: Union[int, str]) -> FieldCal:
    """
    Return field cal with the given ID or name

    :param user_id: current user ID (None if user auth is disabled)
    :param id_or_name: field cal ID (integer) or name

    :return: field cal object
    """
    try:
        try:
            db_field_cal = DbFieldCal.query.get(int(id_or_name))
        except ValueError:
            db_field_cal = None
        else:
            if db_field_cal.user_id != user_id:
                db_field_cal = None
        if db_field_cal is None:
            # Try getting by name
            db_field_cal = DbFieldCal.query.filter(DbFieldCal.name == id_or_name).one_or_none()
        if db_field_cal is None or db_field_cal.user_id != user_id:
            raise UnknownFieldCalError(id=id_or_name)

        # Convert to data model object
        return FieldCal(db_field_cal)
    except Exception:
        db.session.rollback()
        raise


def create_field_cal(user_id: Optional[int], field_cal: FieldCal) -> FieldCal:
    """
    Create a new field cal with the given parameters

    :param user_id: current user ID (None if user auth is disabled)
    :param field_cal: field cal object containing all relevant parameters

    :return: new field cal object
    """
    try:
        if DbFieldCal.query.filter_by(name=field_cal.name).count():
            raise DuplicateFieldCalError(name=field_cal.name)

        # Ignore field cal ID if provided
        kw = field_cal.to_dict()
        try:
            del kw['id']
        except KeyError:
            pass

        # Create new db field cal object
        db_field_cal = DbFieldCal(**kw)
        db_field_cal.user_id = user_id
        db.session.add(db_field_cal)
        db.session.flush()
        field_cal = FieldCal(db_field_cal)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return field_cal


def update_field_cal(user_id: Optional[int], field_cal_id: int, field_cal: FieldCal) -> FieldCal:
    """
    Update an existing field cal

    :param user_id: current user ID (None if user auth is disabled)
    :param field_cal_id: field cal ID to update
    :param field_cal: field cal object containing updated parameters

    :return: updated field cal object
    """
    try:
        db_field_cal = DbFieldCal.query.get(field_cal_id)
        if db_field_cal is None or db_field_cal.user_id != user_id:
            raise UnknownFieldCalError(id=field_cal_id)

        for key, val in field_cal.to_dict().items():
            if key in ('id', 'user_id'):
                # Don't allow changing field cal ID and user
                continue
            if key == 'name' and val != db_field_cal.name and DbFieldCal.query.filter_by(name=val).count():
                raise DuplicateFieldCalError(name=val)
            setattr(db_field_cal, key, val)

        field_cal = FieldCal(db_field_cal)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return field_cal


def delete_field_cal(user_id: Optional[int], field_cal_id: int) -> None:
    """
    Delete field cal with the given ID

    :param user_id: current user ID (None if user auth is disabled)
    :param field_cal_id: field cal ID to delete
    """
    try:
        db_field_cal = DbFieldCal.query.get(field_cal_id)
        if db_field_cal is None or db_field_cal.user_id != user_id:
            raise UnknownFieldCalError(id=field_cal_id)

        db.session.delete(db_field_cal)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
