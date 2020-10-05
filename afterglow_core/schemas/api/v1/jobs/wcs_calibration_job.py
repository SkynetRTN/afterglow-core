"""
Afterglow Core: WCS calibration job schemas
"""

from typing import List as TList, Optional

from marshmallow.fields import Float, Integer, List, Nested

from .... import AfterglowSchema, Boolean
from ..job import JobSchema, JobResultSchema
from .source_extraction_job import SourceExtractionSettingsSchema


__all__ = [
    'WcsCalibrationSettingsSchema', 'WcsCalibrationJobResultSchema',
    'WcsCalibrationJobSchema',
]


class WcsCalibrationSettingsSchema(AfterglowSchema):
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


class WcsCalibrationJobResultSchema(JobResultSchema):
    file_ids = List(Integer(), default=[])  # type: TList[int]


class WcsCalibrationJobSchema(JobSchema):
    type = 'wcs_calibration'

    result = Nested(
        WcsCalibrationJobResultSchema,
        default={})  # type: WcsCalibrationJobResultSchema
    file_ids = List(Integer(), default=[])  # type: TList[int]
    settings = Nested(
        WcsCalibrationSettingsSchema,
        default={})  # type: WcsCalibrationSettingsSchema
    source_extraction_settings = Nested(
        SourceExtractionSettingsSchema,
        default=None)  # type: SourceExtractionSettingsSchema
    inplace = Boolean(default=False)  # type: bool
