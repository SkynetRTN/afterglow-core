"""
Afterglow Core: image cropping job schemas
"""

from marshmallow.fields import Integer, List, Nested

from .. import AfterglowSchema, Boolean
from . import Job, JobResult


__all__ = ['CroppingSettings', 'CroppingJobResult', 'CroppingJobSchema']


class CroppingSettings(AfterglowSchema):
    left = Integer(default=0)  # type: int
    right = Integer(default=0)  # type: int
    top = Integer(default=0)  # type: int
    bottom = Integer(default=0)  # type: int


class CroppingJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: list


class CroppingJobSchema(Job):
    result = Nested(CroppingJobResult, default={})  # type: CroppingJobResult
    file_ids = List(Integer(), default=[])  # type: list
    settings = Nested(CroppingSettings, default={})  # type: CroppingSettings
    inplace = Boolean(default=False)  # type: bool
