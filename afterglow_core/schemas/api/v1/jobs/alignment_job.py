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
    ref_image: str = String(default='central')
    wcs_grid_points: int = Integer(default=0)


class AlignmentJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), default=[])


class AlignmentJobSchema(JobSchema):
    type = 'alignment'

    result: AlignmentJobResultSchema = Nested(
        AlignmentJobResultSchema, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    settings: AlignmentSettingsSchema = Nested(
        AlignmentSettingsSchema, default={})
    sources: TList[SourceExtractionDataSchema] = List(
        Nested(SourceExtractionDataSchema), default=[])
    inplace: bool = Boolean(default=False)
