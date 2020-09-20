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
    pos_type = String(default='auto')  # type: str
    tol = Float(default=None)  # type: float


class SourceMergeJobResultSchema(JobResultSchema):
    data = List(Nested(SourceExtractionDataSchema),
                default=[])  # type: TList[SourceExtractionDataSchema]


class SourceMergeJobSchema(JobSchema):
    result = Nested(
        SourceMergeJobResultSchema)  # type: SourceMergeJobResultSchema
    sources = List(Nested(
        SourceExtractionDataSchema))  # type: TList[SourceExtractionDataSchema]
    settings = Nested(
        SourceMergeSettingsSchema,
        default={})  # type: SourceMergeSettingsSchema
