"""
Afterglow Core: image stacking job schemas
"""

from marshmallow.fields import List, Nested, String, Integer

from .... import AfterglowSchema, Float
from ..job import Job, JobResult


__all__ = ['StackingSettings', 'StackingJobResult', 'StackingJobSchema']


class StackingSettings(AfterglowSchema):
    mode = String(default='average')  # type: str
    scaling = String(default=None)  # type: str
    rejection = String(default=None)  # type: str
    percentile = Integer(default=50)  # type: int
    lo = Float(default=0)  # type: float
    hi = Float(default=100)  # type: float


class StackingJobResult(JobResult):
    file_id = Integer()  # type: int


class StackingJobSchema(Job):
    result = Nested(StackingJobResult, default={})  # type: StackingJobResult
    file_ids = List(Integer(), default=[])  # type: list
    # alignment_settings = Nested(
    #     AlignmentSettings, default={})  # type: AlignmentSettings
    stacking_settings = Nested(
        StackingSettings, default={})  # type: StackingSettings
