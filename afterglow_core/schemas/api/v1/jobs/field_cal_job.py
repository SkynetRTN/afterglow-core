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
    data: TList[FieldCalResultSchema] = List(
        Nested(FieldCalResultSchema), default=[])


class FieldCalJobSchema(JobSchema):
    type = 'field_cal'

    result: FieldCalJobResultSchema = Nested(
        FieldCalJobResultSchema, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    field_cal: FieldCalSchema = Nested(FieldCalSchema, default={})
    source_extraction_settings: SourceExtractionSettingsSchema = Nested(
        SourceExtractionSettingsSchema, default=None)
    photometry_settings: PhotSettingsSchema = Nested(
        PhotSettingsSchema, default=None)
