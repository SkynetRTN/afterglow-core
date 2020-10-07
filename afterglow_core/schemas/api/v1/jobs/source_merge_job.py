"""
Afterglow Core: source merge job schemas
"""

from typing import List as TList

from marshmallow.fields import List, Nested, String

from .... import AfterglowSchema, Float
from ..job import JobSchema, JobResultSchema
from ..source_extraction import SourceExtractionDataSchema


__all__ = [
    'SourceMergeSettingsSchema', 'SourceMergeJobResultSchema',
    'SourceMergeJobSchema',
]


class SourceMergeSettingsSchema(AfterglowSchema):
    pos_type: str = String(default='auto')
    tol: float = Float(default=None)


class SourceMergeJobResultSchema(JobResultSchema):
    data: TList[SourceExtractionDataSchema] = List(
        Nested(SourceExtractionDataSchema), default=[])


class SourceMergeJobSchema(JobSchema):
    type = 'source_merge'

    result: SourceMergeJobResultSchema = Nested(SourceMergeJobResultSchema)
    sources: TList[SourceExtractionDataSchema] = List(Nested(
        SourceExtractionDataSchema))
    settings: SourceMergeSettingsSchema = Nested(
        SourceMergeSettingsSchema, default={})
