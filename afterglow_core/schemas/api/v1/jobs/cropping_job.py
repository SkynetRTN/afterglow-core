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
    left: int = Integer(dump_default=0)
    right: int = Integer(dump_default=0)
    top: int = Integer(dump_default=0)
    bottom: int = Integer(dump_default=0)


class CroppingJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class CroppingJobSchema(JobSchema):
    type = 'cropping'

    result: CroppingJobResultSchema = Nested(
        CroppingJobResultSchema, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: CroppingSettingsSchema = Nested(
        CroppingSettingsSchema, dump_default={})
    inplace: bool = Boolean(dump_default=False)
