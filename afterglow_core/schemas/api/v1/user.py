"""
Afterglow Core: user schemas
"""

from datetime import date, datetime
from typing import List as ListType

from marshmallow.fields import Integer, List, Nested, String

from ... import AfterglowSchema, Boolean, Date, DateTime


__all__ = ['RoleSchema', 'UserSchema', 'TokenSchema']


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
    birth_date = Date()  # type: date
    active = Boolean()  # type: bool
    created_at = DateTime()  # type: datetime
    modified_at = DateTime()  # type: datetime
    roles = List(
        Nested(RoleSchema, only=['name']))  # type: ListType[RoleSchema]
    settings = String()  # type: str


class TokenSchema(AfterglowSchema):
    id = Integer()  # type: int
    user_id = Integer()  # type: int
    token_type = String()  # type: str
    access_token = String()  # type: str
    issued_at = Integer()  # type: int
    expires_in = Integer()  # type: int
    note = String()  # type: str
