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
    x = Integer(default=1)  # type: int
    y = Integer(default=1)  # type: int
    width = Integer(default=0)  # type: int
    height = Integer(default=0)  # type: int
    threshold = Float(default=2.5)  # type: float
    bk_size = Float(default=1/64)  # type: float
    bk_filter_size = Integer(default=3)  # type: int
    fwhm = Float(default=0)  # type: float
    ratio = Float(default=1)  # type: float
    theta = Float(default=0)  # type: float
    min_pixels = Integer(default=3)  # type: int
    deblend = Boolean(default=False)  # type: bool
    deblend_levels = Integer(default=32)  # type: int
    deblend_contrast = Float(default=0.005)  # type: float
    gain = Float(default=None)  # type: float
    clean = Float(default=1)  # type: float
    centroid = Boolean(default=True)  # type: bool
    limit = Integer(default=None)  # type: int


class SourceExtractionJobResultSchema(JobResultSchema):
    data = List(Nested(SourceExtractionDataSchema),
                default=[])  # type: TList[SourceExtractionDataSchema]


class SourceExtractionJobSchema(JobSchema):
    result = Nested(
        SourceExtractionJobResultSchema
    )  # type: SourceExtractionJobResultSchema
    file_ids = List(Integer(), default=[])  # type: TList[int]
    source_extraction_settings = Nested(
        SourceExtractionSettingsSchema,
        default={})  # type: SourceExtractionSettingsSchema
    merge_sources = Boolean(default=True)  # type: bool
    source_merge_settings = Nested(
        SourceMergeSettingsSchema,
        default={})  # type: SourceMergeSettingsSchema
