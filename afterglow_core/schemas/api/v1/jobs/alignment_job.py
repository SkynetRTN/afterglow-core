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
    ref_image: str = String(dump_default='central')
    wcs_grid_points: int = Integer(dump_default=0)
    prefilter: bool = Boolean(dump_default=True)


class AlignmentJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class AlignmentJobSchema(JobSchema):
    type = 'alignment'

    result: AlignmentJobResultSchema = Nested(
        AlignmentJobResultSchema, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: AlignmentSettingsSchema = Nested(
        AlignmentSettingsSchema, dump_default={})
    sources: TList[SourceExtractionDataSchema] = List(
        Nested(SourceExtractionDataSchema), dump_default=[])
    inplace: bool = Boolean(dump_default=False)
    crop: bool = Boolean(dump_default=False)
