"""
Afterglow Core: image cropping job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested

from .... import AfterglowSchema, Boolean
from ..job import JobSchema, JobResultSchema


__all__ = ['CroppingSettingsSchema', 'CroppingJobResultSchema',
           'CroppingJobSchema']


class CroppingSettingsSchema(AfterglowSchema):
    left = Integer(default=0)  # type: int
    right = Integer(default=0)  # type: int
    top = Integer(default=0)  # type: int
    bottom = Integer(default=0)  # type: int


class CroppingJobResultSchema(JobResultSchema):
    file_ids = List(Integer(), default=[])  # type: TList[int]


class CroppingJobSchema(JobSchema):
    result = Nested(
        CroppingJobResultSchema, default={})  # type: CroppingJobResultSchema
    file_ids = List(Integer(), default=[])  # type: TList[int]
    settings = Nested(
        CroppingSettingsSchema, default={})  # type: CroppingSettingsSchema
    inplace = Boolean(default=False)  # type: bool
