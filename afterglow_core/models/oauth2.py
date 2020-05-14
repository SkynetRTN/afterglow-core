"""
Afterglow Core: oauth2 schemas
"""

from datetime import datetime
from typing import List as ListType

from marshmallow.fields import Integer, List, Nested, String

from . import AfterglowSchema, Boolean, DateTime
from .user import UserSchema


__all__ = ['OAuth2TokenSchema']


class OAuth2TokenSchema(AfterglowSchema):
    client_id = String()  # type: str
    token_type = String()  # type: str
    access_token = String()  # type: str
    refresh_token = String()  # type: str
    scope = String()  # type: str
    revoked = Boolean()  # type: bool
    issued_at = Integer()  # type: int
    expires_in = Integer()  # type: int
    id = Integer() #type: int
    user_id = Integer() #type: int
    note = String()  # type: str