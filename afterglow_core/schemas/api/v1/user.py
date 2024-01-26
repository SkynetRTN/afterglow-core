"""
Afterglow Core: user schemas
"""

from datetime import date, datetime
from typing import List as ListType

from marshmallow.fields import Integer, List, Nested, String

from ... import AfterglowSchema, Boolean, DateTime, Resource


__all__ = ['RoleSchema', 'UserSchema', 'TokenSchema']


class RoleSchema(AfterglowSchema):
    id: int = Integer()
    name: str = String()
    description: str = String()


class UserSchema(Resource):
    __get_view__ = 'users.users'

    id: int = Integer()
    username: str = String()
    active: bool = Boolean()
    created_at: datetime = DateTime()
    modified_at: datetime = DateTime()
    roles: ListType[RoleSchema] = List(Nested(RoleSchema, only=['name']))
    settings: str = String()
    email: str = String()
    first_name: str = String()
    last_name: str = String()


class TokenSchema(Resource):
    __get_view__ = 'ajax_api.tokens'

    id: int = Integer()
    user_id: int = Integer()
    token_type: str = String()
    access_token: str = String()
    issued_at: int = Integer()
    expires_in: int = Integer()
    note: str = String()
