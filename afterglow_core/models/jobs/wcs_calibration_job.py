"""
Afterglow Core: WCS calibration job schemas
"""

from typing import List as TList, Optional

from marshmallow.fields import Float, String, Integer, List, Nested

from .. import AfterglowSchema, Boolean
from .source_extraction_job import SourceExtractionSettings
from . import Job, JobResult


__all__ = [
    'WcsCalibrationSettings', 'WcsCalibrationJobResult',
    'WcsCalibrationJobSchema',
]


class WcsCalibrationSettings(AfterglowSchema):
    ra_hours = Float(default=0)  # type: float
    dec_degs = Float(default=0)  # type: float
    radius = Float(default=180)  # type: float
    min_scale = Float(default=0.1)  # type: float
    max_scale = Float(default=60)  # type: float
    parity = Boolean(
        truthy={True, 1, 'negative'},
        falsy={False, 0, 'positive'}, default=None)  # type: Optional[bool]
    sip_order = Integer(default=3)  # type: int
    crpix_center = Boolean(default=True)  # type: bool
    max_sources = Integer(default=100)  # type: Optional[int]


class WcsCalibrationJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: TList[int]


class WcsCalibrationJobSchema(Job):
    result = Nested(
        WcsCalibrationJobResult, default={})  # type: WcsCalibrationJobResult
    file_ids = List(Integer(), default=[])  # type: list
    settings = Nested(
        WcsCalibrationSettings, default={})  # type: WcsCalibrationSettings
    source_extraction_settings = Nested(
        SourceExtractionSettings,
        default=None)  # type: SourceExtractionSettings
    inplace = Boolean(default=False)  # type: bool
