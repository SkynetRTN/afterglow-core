"""
Afterglow Core: source extraction job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested

from .... import AfterglowSchema, Boolean, Float
from ..job import JobSchema, JobResultSchema
from ..source_extraction import SourceExtractionDataSchema
from .source_merge_job import SourceMergeSettingsSchema


__all__ = [
    'SourceExtractionSettingsSchema', 'SourceExtractionJobResultSchema', 'SourceExtractionJobSchema',
]


class SourceExtractionSettingsSchema(AfterglowSchema):
    x: int = Integer(dump_default=1)
    y: int = Integer(dump_default=1)
    width: int = Integer(dump_default=0)
    height: int = Integer(dump_default=0)
    downsample: int = Integer(dump_default=2)
    threshold: float = Float(dump_default=2.5)
    bk_size: float = Float(dump_default=1/64)
    bk_filter_size: int = Integer(dump_default=3)
    fwhm: float = Float(dump_default=0)
    ratio: float = Float(dump_default=1)
    theta: float = Float(dump_default=0)
    min_pixels: int = Integer(dump_default=3)
    min_fwhm: float = Float(dump_default=0.8)
    max_fwhm: float = Float(dump_default=10)
    max_ellipticity: float = Float(dump_default=2)
    deblend: bool = Boolean(dump_default=False)
    deblend_levels: int = Integer(dump_default=32)
    deblend_contrast: float = Float(dump_default=0.005)
    gain: float = Float(dump_default=None)
    clean: float = Float(dump_default=1)
    centroid: bool = Boolean(dump_default=True)
    limit: int = Integer(dump_default=None)
    sat_level: float = Float(dump_default=63000)
    auto_sat_level: bool = Boolean(dump_default=False)
    discard_saturated: int = Integer(dump_default=1)
    max_sources: int = Integer(dump_default=10000)
    clip_lo: float = Float(dump_default=0)
    clip_hi: float = Float(dump_default=100)


class SourceExtractionJobResultSchema(JobResultSchema):
    data: TList[SourceExtractionDataSchema] = List(Nested(SourceExtractionDataSchema), dump_default=[])


class SourceExtractionJobSchema(JobSchema):
    type = 'source_extraction'

    result: SourceExtractionJobResultSchema = Nested(SourceExtractionJobResultSchema)
    file_ids: TList[int] = List(Integer(), dump_default=[])
    source_extraction_settings: SourceExtractionSettingsSchema = Nested(SourceExtractionSettingsSchema, dump_default={})
    merge_sources: bool = Boolean(dump_default=True)
    source_merge_settings: SourceMergeSettingsSchema = Nested(SourceMergeSettingsSchema, dump_default={})
