"""
Afterglow Core: error response model
"""

from marshmallow.fields import Dict, String

from ..schemas import AfterglowSchema


__all__ = ['AfterglowError']


class AfterglowError(AfterglowSchema):
    """
    Afterglow error schema

    Attributes::
        status: HTTP status
        id: unique string error code
        detail: detailed error description
        meta: optional error-specific metadata
    """
    status: str = String()
    id: str = String()
    detail: str = String()
    meta: dict = Dict()
