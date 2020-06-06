"""
Afterglow Core: source extraction job schemas
"""

from marshmallow.fields import Integer, List, Nested

from .. import AfterglowSchema, Boolean, Float
from ..source_extraction import SourceExtractionData
from . import Job, JobResult
from .source_merge_job import SourceMergeSettings


__all__ = [
    'SourceExtractionSettings', 'SourceExtractionJobResult',
    'SourceExtractionJobSchema',
]


class SourceExtractionSettings(AfterglowSchema):
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


class SourceExtractionJobResult(JobResult):
    data = List(Nested(SourceExtractionData), default=[])  # type: list


class SourceExtractionJobSchema(Job):
    result = Nested(
        SourceExtractionJobResult)  # type: SourceExtractionJobResult
    file_ids = List(Integer(), default=[])  # type: list
    source_extraction_settings = Nested(
        SourceExtractionSettings, default={})  # type: SourceExtractionSettings
    merge_sources = Boolean(default=True)  # type: bool
    source_merge_settings = Nested(
        SourceMergeSettings, default={})  # type: SourceMergeSettings
