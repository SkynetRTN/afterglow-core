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
    ra_hours: Optional[float] = Float(default=None)
    dec_degs: Optional[float] = Float(default=None)
    radius: float = Float(default=180)
    min_scale: float = Float(default=0.1)
    max_scale: float = Float(default=60)
    parity: Optional[bool] = Boolean(
        truthy={True, 1, 'negative'},
        falsy={False, 0, 'positive'}, default=None)
    sip_order: int = Integer(default=3)
    crpix_center: bool = Boolean(default=True)
    max_sources: Optional[int] = Integer(default=100)


class WcsCalibrationJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), default=[])


class WcsCalibrationJobSchema(JobSchema):
    type = 'wcs_calibration'

    result: WcsCalibrationJobResultSchema = Nested(
        WcsCalibrationJobResultSchema, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    settings: WcsCalibrationSettingsSchema = Nested(
        WcsCalibrationSettingsSchema, default={})
    source_extraction_settings: SourceExtractionSettingsSchema = Nested(
        SourceExtractionSettingsSchema, default=None)
    inplace: bool = Boolean(default=False)
