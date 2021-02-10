"""
Afterglow Core: user schemas
"""

from datetime import date, datetime
from typing import List as ListType

from marshmallow.fields import Integer, List, Nested, String

from ... import AfterglowSchema, Boolean, Date, DateTime, Resource


__all__ = ['RoleSchema', 'MinorUserSchema', 'UserSchema']


class RoleSchema(AfterglowSchema):
    id: int = Integer()
    name: str = String()
    description: str = String()


class MinorUserSchema(Resource):
    __get_view__ = 'users'

    id: int = Integer()
    username: str = String()
    active: bool = Boolean()
    created_at: datetime = DateTime()
    modified_at: datetime = DateTime()
    roles: ListType[RoleSchema] = List(Nested(RoleSchema, only=['name']))
    settings: str = String()


class UserSchema(MinorUserSchema):
    email: str = String()
    first_name: str = String()
    last_name: str = String()
    birth_date: date = Date()
