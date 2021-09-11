"""
Afterglow Core: common definitions for SQLA declarative data models
"""

import json
from datetime import datetime

from sqlalchemy import types

from .. import AfterglowSchemaEncoder


__all__ = ['Date', 'DateTime', 'JSONType', 'Time']


# noinspection PyAbstractClass
class JSONType(types.TypeDecorator):
    """
    Text column that contains a JSON data structure; a simplified version of
    :class:`sqlalchemy_utils.types.json.JSONType`, which can be initialized
    both from a JSON structure and a JSON string
    """
    impl = types.UnicodeText
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and not isinstance(value, str):
            value = json.dumps(value, cls=AfterglowSchemaEncoder)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


# noinspection PyAbstractClass
class DateTime(types.TypeDecorator):
    """
    DateTime column that can be assigned an ISO-formatted string
    """
    impl = types.DateTime

    def process_bind_param(self, value, dialect):
        if value is not None and not isinstance(value, datetime):
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        return value


# noinspection PyAbstractClass
class Date(types.TypeDecorator):
    """
    Date column that can be assigned an ISO-formatted string
    """
    impl = types.Date

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime):
            value = value.date()
        elif value is not None and not isinstance(value, datetime):
            value = datetime.strptime(value, '%Y-%m-%d')
        return value


# noinspection PyAbstractClass
class Time(types.TypeDecorator):
    """
    Time column that can be assigned an ISO-formatted string
    """
    impl = types.Time

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime):
            value = value.time()
        elif value is not None and not isinstance(value, datetime):
            value = datetime.strptime(value, '%H:%M:%S.%f')
        return value
