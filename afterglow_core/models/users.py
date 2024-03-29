"""
Afterglow Core: user data models
"""

from datetime import date, datetime
from typing import List as TList

from marshmallow.fields import Integer, List, Nested, String

from ..schemas import AfterglowSchema, Boolean, Date, DateTime


__all__ = ['Identity', 'Role', 'Token', 'User', 'UserClient']


class Role(AfterglowSchema):
    id: int = Integer()
    name: str = String()
    description: str = String()


class Identity(AfterglowSchema):
    id: int = Integer()
    name: str = String()
    user_id: int = Integer()
    auth_method: str = String()
    data: str = String(dump_default='')


class User(AfterglowSchema):
    id: int = Integer()
    username: str = String()
    password: str = String()
    email: str = String()
    first_name: str = String()
    last_name: str = String()
    active: bool = Boolean()
    created_at: datetime = DateTime()
    modified_at: datetime = DateTime()
    roles: TList[Role] = List(Nested(Role, only=['name']))
    settings: str = String()
    identities: TList[Identity] = List(Nested(
        Identity, only=['id', 'name', 'auth_method', 'data']))


class Token(AfterglowSchema):
    id: int = Integer()
    user_id: int = Integer()
    token_type: str = String()
    access_token: str = String()
    refresh_token: str = String()
    scope: str = String()
    issued_at: int = Integer()
    access_token_revoked_at: int = Integer()
    refresh_token_revoked_at: int = Integer()
    expires_in: int = Integer()
    note: str = String()


class UserClient(AfterglowSchema):
    id: int = Integer()
    user_id: int = Integer()
    client_id: str = String()
