"""
Afterglow Core: photometric calibration job schemas
"""

from marshmallow.fields import Integer, List, Nested

from ..job import Job, JobResult
from ..field_cal import FieldCal, FieldCalResult
from ..photometry import PhotSettings
from .source_extraction_job import SourceExtractionSettings


__all__ = ['FieldCalJobResult', 'FieldCalJobSchema']


class FieldCalJobResult(JobResult):
    data = List(Nested(FieldCalResult), default=[])  # type: list


class FieldCalJobSchema(Job):
    name = 'field_cal'
    description = 'Photometric Calibration'
    result = Nested(
        FieldCalJobResult, default={})  # type: FieldCalJobResult
    file_ids = List(Integer(), default=[])  # type: list
    field_cal = Nested(FieldCal, default={})  # type: FieldCal
    source_extraction_settings = Nested(
        SourceExtractionSettings,
        default=None)  # type: SourceExtractionSettings
    photometry_settings = Nested(
        PhotSettings, default=None)  # type: PhotSettings
