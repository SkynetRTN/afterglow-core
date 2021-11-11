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
    'SourceExtractionSettingsSchema', 'SourceExtractionJobResultSchema',
    'SourceExtractionJobSchema',
]


class SourceExtractionSettingsSchema(AfterglowSchema):
    x: int = Integer(default=1)
    y: int = Integer(default=1)
    width: int = Integer(default=0)
    height: int = Integer(default=0)
    threshold: float = Float(default=2.5)
    bk_size: float = Float(default=1/64)
    bk_filter_size: int = Integer(default=3)
    fwhm: float = Float(default=0)
    ratio: float = Float(default=1)
    theta: float = Float(default=0)
    min_pixels: int = Integer(default=3)
    deblend: bool = Boolean(default=False)
    deblend_levels: int = Integer(default=32)
    deblend_contrast: float = Float(default=0.005)
    gain: float = Float(default=None)
    clean: float = Float(default=1)
    centroid: bool = Boolean(default=True)
    limit: int = Integer(default=None)
    sat_level: float = Float(default=63000)
    discard_saturated: int = Integer(default=1)


class SourceExtractionJobResultSchema(JobResultSchema):
    data: TList[SourceExtractionDataSchema] = List(
        Nested(SourceExtractionDataSchema), default=[])


class SourceExtractionJobSchema(JobSchema):
    type = 'source_extraction'

    result: SourceExtractionJobResultSchema = Nested(
        SourceExtractionJobResultSchema)
    file_ids: TList[int] = List(Integer(), default=[])
    source_extraction_settings: SourceExtractionSettingsSchema = Nested(
        SourceExtractionSettingsSchema, default={})
    merge_sources: bool = Boolean(default=True)
    source_merge_settings: SourceMergeSettingsSchema = Nested(
        SourceMergeSettingsSchema, default={})
