"""
Afterglow Core: user schemas
"""

from datetime import datetime
from typing import List as ListType

from marshmallow.fields import Integer, List, Nested, String

from . import AfterglowSchema, Boolean, DateTime


__all__ = ['RoleSchema', 'UserSchema']


class RoleSchema(AfterglowSchema):
    id = Integer()  # type: int
    name = String()  # type: str
    description = String()  # type: str


class UserSchema(AfterglowSchema):
    id = Integer()  # type: int
    username = String()  # type: str
    email = String()  # type: str
    first_name = String()  # type: str
    last_name = String()  # type: str
    active = Boolean()  # type: bool
    created_at = DateTime()  # type: datetime
    modified_at = DateTime()  # type: datetime
    roles = List(
        Nested(RoleSchema, only=['name']))  # type: ListType[RoleSchema]
    settings = String()  # type: str
