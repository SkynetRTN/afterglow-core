"""
Afterglow Core: user schemas
"""

from datetime import date, datetime
from typing import List as ListType

from marshmallow.fields import Integer, List, Nested, String

from . import AfterglowSchema, Boolean, Date, DateTime


__all__ = ['RoleSchema', 'UserSchema', 'TokenSchema', 'UserProfile']


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


class UserProfile(AfterglowSchema):
    """User profile data retrieved from auth server"""
    id = String(default=None)  # type: str
    username = String(default=None)  # type: str
    email = String(default=None)  # type: str
    first_name = String(default=None)  # type: str
    last_name = String(default=None)  # type: str
    birth_date = Date(default=None)  # type: date

    @property
    def full_name(self):
        return ' '.join(
            ([self.first_name] if self.first_name else []) +
            ([self.last_name] if self.last_name else []))
