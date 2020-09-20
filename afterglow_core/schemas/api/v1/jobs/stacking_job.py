"""
Afterglow Core: image stacking job schemas
"""

from typing import List as TList

from marshmallow.fields import List, Nested, String, Integer

from .... import AfterglowSchema, Float
from ..job import JobSchema, JobResultSchema


__all__ = ['StackingSettingsSchema', 'StackingJobResultSchema',
           'StackingJobSchema']


class StackingSettingsSchema(AfterglowSchema):
    mode = String(default='average')  # type: str
    scaling = String(default=None)  # type: str
    rejection = String(default=None)  # type: str
    percentile = Integer(default=50)  # type: int
    lo = Float(default=0)  # type: float
    hi = Float(default=100)  # type: float


class StackingJobResultSchema(JobResultSchema):
    file_id = Integer()  # type: int


class StackingJobSchema(JobSchema):
    result = Nested(
        StackingJobResultSchema, default={})  # type: StackingJobResultSchema
    file_ids = List(Integer(), default=[])  # type: TList[int]
    # alignment_settings = Nested(
    #     AlignmentSettings, default={})  # type: AlignmentSettings
    stacking_settings = Nested(
        StackingSettingsSchema, default={})  # type: StackingSettingsSchema
