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
    left: int = Integer(default=0)
    right: int = Integer(default=0)
    top: int = Integer(default=0)
    bottom: int = Integer(default=0)


class CroppingJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), default=[])


class CroppingJobSchema(JobSchema):
    type = 'cropping'

    result: CroppingJobResultSchema = Nested(
        CroppingJobResultSchema, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    settings: CroppingSettingsSchema = Nested(
        CroppingSettingsSchema, default={})
    inplace: bool = Boolean(default=False)
