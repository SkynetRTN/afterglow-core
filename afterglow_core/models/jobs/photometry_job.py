"""
Afterglow Core: batch photometry job schemas
"""

from marshmallow.fields import Integer, List, Nested

from ..photometry import PhotSettings, PhotometryData
from ..source_extraction import SourceExtractionData
from . import Job, JobResult


__all__ = ['PhotometryJobResult', 'PhotometryJobSchema']


class PhotometryJobResult(JobResult):
    data = List(Nested(PhotometryData), default=[])  # type: list


class PhotometryJobSchema(Job):
    result = Nested(
        PhotometryJobResult, default={})  # type: PhotometryJobResult
    file_ids = List(Integer(), default=[])  # type: list
    sources = List(Nested(SourceExtractionData), default=[])  # type: list
    settings = Nested(PhotSettings, default={})  # type: PhotSettings
