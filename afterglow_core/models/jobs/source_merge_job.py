"""
Afterglow Core: source merge job schemas
"""

from marshmallow.fields import List, Nested, String

from .. import AfterglowSchema, Float
from ..source_extraction import SourceExtractionData
from . import Job, JobResult


__all__ = [
    'SourceMergeSettings', 'SourceMergeJobResult', 'SourceMergeJobSchema',
]


class SourceMergeSettings(AfterglowSchema):
    pos_type = String(default='auto')  # type: str
    tol = Float(default=None)  # type: float


class SourceMergeJobResult(JobResult):
    data = List(Nested(SourceExtractionData), default=[])  # type: list


class SourceMergeJobSchema(Job):
    result = Nested(SourceMergeJobResult)  # type: SourceMergeJobResult
    sources = List(Nested(SourceExtractionData))  # type: list
    settings = Nested(
        SourceMergeSettings, default={})  # type: SourceMergeSettings
