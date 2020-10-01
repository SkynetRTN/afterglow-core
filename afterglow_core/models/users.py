"""
Afterglow Core: user data models
"""

from datetime import date, datetime
from typing import List as TList

from marshmallow.fields import Integer, List, Nested, String

from ..schemas import AfterglowSchema, Boolean, Date, DateTime


__all__ = ['Identity', 'Role', 'Token', 'User', 'UserClient']


class Role(AfterglowSchema):
    id = Integer()  # type: int
    name = String()  # type: str
    description = String()  # type: str


class Identity(AfterglowSchema):
    id = Integer()  # type: int
    name = String()  # type: str
    user_id = Integer()  # type: int
    auth_method = String()  # type: str
    data = String(default='')  # type: str


class User(AfterglowSchema):
    id = Integer()  # type: int
    username = String()  # type: str
    password = String()  # type: str
    email = String()  # type: str
    first_name = String()  # type: str
    last_name = String()  # type: str
    birth_date = Date()  # type: date
    active = Boolean()  # type: bool
    created_at = DateTime()  # type: datetime
    modified_at = DateTime()  # type: datetime
    roles = List(Nested(Role, only=['name']))  # type: TList[Role]
    settings = String()  # type: str
    identities = List(
        Nested(Identity, only=['id', 'name']))  # type: TList[Identity]


class Token(AfterglowSchema):
    id = Integer()  # type: int
    user_id = Integer()  # type: int
    token_type = String()  # type: str
    access_token = String()  # type: str
    issued_at = Integer()  # type: int
    expires_in = Integer()  # type: int
    note = String()  # type: str


class UserClient(AfterglowSchema):
    id = Integer()  # type: int
    user_id = Integer()  # type: int
    client_id = String()  # type: str
