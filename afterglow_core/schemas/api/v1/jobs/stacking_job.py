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
    mode: str = String(default='average')
    scaling: str = String(default=None)
    rejection: str = String(default=None)
    percentile: int = Integer(default=50)
    lo: float = Float(default=0)
    hi: float = Float(default=100)


class StackingJobResultSchema(JobResultSchema):
    file_id: int = Integer()


class StackingJobSchema(JobSchema):
    type = 'stacking'

    result: StackingJobResultSchema = Nested(
        StackingJobResultSchema, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    # alignment_settings: AlignmentSettingsSchema = Nested(
    #     AlignmentSettings, default={})
    stacking_settings: StackingSettingsSchema = Nested(
        StackingSettingsSchema, default={})
