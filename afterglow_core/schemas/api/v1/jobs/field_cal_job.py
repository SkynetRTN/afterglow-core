"""
Afterglow Core: photometric calibration job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested

from ..job import JobSchema, JobResultSchema
from ..field_cal import FieldCalSchema, FieldCalResultSchema
from ..photometry import PhotSettingsSchema
from .source_extraction_job import SourceExtractionSettingsSchema


__all__ = ['FieldCalJobResultSchema', 'FieldCalJobSchema']


class FieldCalJobResultSchema(JobResultSchema):
    data = List(
        Nested(FieldCalResultSchema),
        default=[])  # type: TList[FieldCalResultSchema]


class FieldCalJobSchema(JobSchema):
    result = Nested(
        FieldCalJobResultSchema, default={})  # type: FieldCalJobResultSchema
    file_ids = List(Integer(), default=[])  # type: TList[int]
    field_cal = Nested(FieldCalResultSchema, default={})  # type: FieldCalSchema
    source_extraction_settings = Nested(
        SourceExtractionSettingsSchema,
        default=None)  # type: SourceExtractionSettingsSchema
    photometry_settings = Nested(
        PhotSettingsSchema, default=None)  # type: PhotSettingsSchema
