"""
Afterglow Core: image stacking job schemas
"""

from typing import List as TList, Optional

from marshmallow.fields import List, Nested, String, Integer

from .... import AfterglowSchema, Boolean, Float
from ..job import JobSchema, JobResultSchema


__all__ = ['StackingSettingsSchema', 'StackingJobResultSchema',
           'StackingJobSchema']


class StackingSettingsSchema(AfterglowSchema):
    mode: str = String(dump_default='average')
    scaling: str = String(dump_default=None)
    rejection: str = String(dump_default=None)
    propagate_mask: bool = Boolean(dump_default=True)
    percentile: int = Integer(dump_default=50)
    lo: float = Float(dump_default=0)
    hi: float = Float(dump_default=100)
    smart_stacking: Optional[str] = String(dump_default=None)


class StackingJobResultSchema(JobResultSchema):
    file_id: int = Integer()


class StackingJobSchema(JobSchema):
    type = 'stacking'

    result: StackingJobResultSchema = Nested(
        StackingJobResultSchema, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    # alignment_settings: AlignmentSettingsSchema = Nested(
    #     AlignmentSettings, dump_default={})
    stacking_settings: StackingSettingsSchema = Nested(
        StackingSettingsSchema, dump_default={})
