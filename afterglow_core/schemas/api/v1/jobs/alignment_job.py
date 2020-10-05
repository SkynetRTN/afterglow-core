"""
Afterglow Core: image alignment job schemas
"""

from typing import List as TList

from marshmallow.fields import String, Integer, List, Nested

from .... import AfterglowSchema, Boolean
from ..job import JobSchema, JobResultSchema
from ..source_extraction import SourceExtractionDataSchema


__all__ = ['AlignmentSettingsSchema', 'AlignmentJobResultSchema',
           'AlignmentJobSchema']


class AlignmentSettingsSchema(AfterglowSchema):
    ref_image = String(default='central')  # type: str
    wcs_grid_points = Integer(default=0)  # type: int


class AlignmentJobResultSchema(JobResultSchema):
    file_ids = List(Integer(), default=[])  # type: TList[int]


class AlignmentJobSchema(JobSchema):
    type = 'alignment'

    result = Nested(
        AlignmentJobResultSchema, default={})  # type: AlignmentJobResultSchema
    file_ids = List(Integer(), default=[])  # type: TList[int]
    settings = Nested(
        AlignmentSettingsSchema, default={})  # type: AlignmentSettingsSchema
    sources = List(
        Nested(SourceExtractionDataSchema),
        default=[])  # type: TList[SourceExtractionDataSchema]
    inplace = Boolean(default=False)  # type: bool
