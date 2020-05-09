"""
Afterglow Core: image alignment job schemas
"""

from marshmallow.fields import String, Integer, List, Nested

from .. import AfterglowSchema, Boolean
from ..source_extraction import SourceExtractionData
from . import Job, JobResult


__all__ = ['AlignmentSettings', 'AlignmentJobResult', 'AlignmentJobSchema']


class AlignmentSettings(AfterglowSchema):
    ref_image = String(default='central')  # type: str
    wcs_grid_points = Integer(default=0)  # type: int


class AlignmentJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: list


class AlignmentJobSchema(Job):
    result = Nested(AlignmentJobResult, default={})  # type: AlignmentJobResult
    file_ids = List(Integer(), default=[])  # type: list
    settings = Nested(AlignmentSettings, default={})  # type: AlignmentSettings
    sources = List(Nested(SourceExtractionData), default=[])  # type: list
    inplace = Boolean(default=False)  # type: bool
