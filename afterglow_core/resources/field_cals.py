"""
Afterglow Core: photometric field calibration prescriptions resource
"""

from typing import Optional, Union

from sqlalchemy import Column, Float, Integer, String

from ..schemas.api.v1 import FieldCalSchema
from ..errors.field_cal import UnknownFieldCalError
from .data_files import Base, get_data_file_db


__all__ = ['SqlaFieldCal', 'get_field_cal']


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


def get_field_cal(user_id: Optional[int],
                  id_or_name: Union[int, str]) -> FieldCalSchema:
    """
    Return field cal with the given ID or name

    :param user_id: current user ID (None if user auth is disabled)
    :param id_or_name: field cal ID (integer) or name

    :return: field cal schema
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
    return FieldCalSchema.from_db(field_cal)
