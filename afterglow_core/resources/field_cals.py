"""
Afterglow Core: photometric field calibration prescriptions resource
"""

from typing import List as TList, Optional, Union

from sqlalchemy import Column, Float, Integer, String

from ..models import FieldCal
from ..errors.field_cal import DuplicateFieldCalError, UnknownFieldCalError
from .base import JSONType
from .data_files import DataFileBase, get_data_file_db


__all__ = [
    'query_field_cals', 'get_field_cal', 'create_field_cal', 'update_field_cal',
    'delete_field_cal',
]


class DbFieldCal(DataFileBase):
    __tablename__ = 'field_cals'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(1024), unique=True, nullable=False, index=True)
    catalog_sources = Column(JSONType)
    catalogs = Column(JSONType)
    custom_filter_lookup = Column(JSONType)
    source_inclusion_percent = Column(Float)
    min_snr = Column(Float, server_default='0')
    max_snr = Column(Float, server_default='0')
    source_match_tol = Column(Float)


def query_field_cals(user_id: Optional[int]) -> TList[FieldCal]:
    """
    Return all user's field cals

    :param user_id: current user ID (None if user auth is disabled)

    :return: list of field cal objects
    """
    adb = get_data_file_db(user_id)
    try:
        return [FieldCal(db_field_cal)
                for db_field_cal in adb.query(DbFieldCal)]
    finally:
        adb.remove()


def get_field_cal(user_id: Optional[int],
                  id_or_name: Union[int, str]) -> FieldCal:
    """
    Return field cal with the given ID or name

    :param user_id: current user ID (None if user auth is disabled)
    :param id_or_name: field cal ID (integer) or name

    :return: field cal object
    """
    adb = get_data_file_db(user_id)
    try:
        try:
            db_field_cal = adb.query(DbFieldCal).get(int(id_or_name))
        except ValueError:
            db_field_cal = None
        if db_field_cal is None:
            # Try getting by name
            db_field_cal = adb.query(DbFieldCal).filter(
                DbFieldCal.name == id_or_name).one_or_none()
        if db_field_cal is None:
            raise UnknownFieldCalError(id=id_or_name)

        # Convert to data model object
        return FieldCal(db_field_cal)
    finally:
        adb.remove()


def create_field_cal(user_id: Optional[int], field_cal: FieldCal) -> FieldCal:
    """
    Create a new field cal with the given parameters

    :param user_id: current user ID (None if user auth is disabled)
    :param field_cal: field cal object containing all relevant parameters

    :return: new field cal object
    """
    adb = get_data_file_db(user_id)
    try:
        if adb.query(DbFieldCal).filter(DbFieldCal.name == field_cal.name) \
                .count():
            raise DuplicateFieldCalError(name=field_cal.name)

        # Ignore field cal ID if provided
        kw = field_cal.to_dict()
        try:
            del kw['id']
        except KeyError:
            pass

        # Create new db field cal object
        try:
            db_field_cal = DbFieldCal(**kw)
            adb.add(db_field_cal)
            adb.flush()
            field_cal = FieldCal(db_field_cal)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return field_cal
    finally:
        adb.remove()


def update_field_cal(user_id: Optional[int], field_cal_id: int,
                     field_cal: FieldCal) -> FieldCal:
    """
    Update the existing field cal

    :param user_id: current user ID (None if user auth is disabled)
    :param field_cal_id: field cal ID to update
    :param field_cal: field cal object containing updated parameters

    :return: updated field cal object
    """
    adb = get_data_file_db(user_id)
    try:
        db_field_cal = adb.query(DbFieldCal).get(field_cal_id)
        if db_field_cal is None:
            raise UnknownFieldCalError(id=field_cal_id)

        for key, val in field_cal.to_dict().items():
            if key == 'id':
                # Don't allow changing field cal ID
                continue
            if key == 'name' and val != db_field_cal.name and adb.query(
                    DbFieldCal).filter(DbFieldCal.name == val).count():
                raise DuplicateFieldCalError(name=val)
            setattr(db_field_cal, key, val)
        try:
            field_cal = FieldCal(db_field_cal)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return field_cal
    finally:
        adb.remove()


def delete_field_cal(user_id: Optional[int], field_cal_id: int) -> None:
    """
    Delete field cal with the given ID

    :param user_id: current user ID (None if user auth is disabled)
    :param field_cal_id: field cal ID to delete
    """
    adb = get_data_file_db(user_id)
    try:
        db_field_cal = adb.query(DbFieldCal).get(field_cal_id)
        if db_field_cal is None:
            raise UnknownFieldCalError(id=field_cal_id)

        try:
            adb.delete(db_field_cal)
            adb.commit()
        except Exception:
            adb.rollback()
            raise
    finally:
        adb.remove()
