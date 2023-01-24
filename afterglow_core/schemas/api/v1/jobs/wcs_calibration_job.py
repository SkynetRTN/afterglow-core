"""
Afterglow Core: WCS calibration job schemas
"""

from typing import List as TList, Optional

from marshmallow.fields import Integer, List, Nested

from .... import AfterglowSchema, Boolean, Float
from ..job import JobSchema, JobResultSchema
from .source_extraction_job import SourceExtractionSettingsSchema


__all__ = [
    'WcsCalibrationSettingsSchema', 'WcsCalibrationJobResultSchema',
    'WcsCalibrationJobSchema',
]


class WcsCalibrationSettingsSchema(AfterglowSchema):
    ra_hours: Optional[float] = Float(dump_default=None)
    dec_degs: Optional[float] = Float(dump_default=None)
    radius: float = Float(dump_default=180)
    min_scale: float = Float(dump_default=0.1)
    max_scale: float = Float(dump_default=60)
    parity: Optional[bool] = Boolean(
        truthy={True, 1, 'negative'},
        falsy={False, 0, 'positive'}, dump_default=None)
    sip_order: int = Integer(dump_default=3)
    crpix_center: bool = Boolean(dump_default=True)
    max_sources: Optional[int] = Integer(dump_default=100)


class WcsCalibrationJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class WcsCalibrationJobSchema(JobSchema):
    type = 'wcs_calibration'

    result: WcsCalibrationJobResultSchema = Nested(
        WcsCalibrationJobResultSchema, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: WcsCalibrationSettingsSchema = Nested(
        WcsCalibrationSettingsSchema, dump_default={})
    source_extraction_settings: SourceExtractionSettingsSchema = Nested(
        SourceExtractionSettingsSchema, dump_default=None)
    inplace: bool = Boolean(dump_default=True)
