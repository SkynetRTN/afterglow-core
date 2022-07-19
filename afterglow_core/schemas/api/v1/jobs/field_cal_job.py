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
        Nested(FieldCalResultSchema), dump_default=[])


class FieldCalJobSchema(JobSchema):
    type = 'field_cal'

    result: FieldCalJobResultSchema = Nested(
        FieldCalJobResultSchema, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    field_cal: FieldCalSchema = Nested(FieldCalSchema, dump_default={})
    source_extraction_settings: SourceExtractionSettingsSchema = Nested(
        SourceExtractionSettingsSchema, dump_default=None)
    photometry_settings: PhotSettingsSchema = Nested(
        PhotSettingsSchema, dump_default=None)
