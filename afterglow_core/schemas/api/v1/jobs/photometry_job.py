"""
Afterglow Core: batch photometry job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested

from ..job import JobSchema, JobResultSchema
from ..photometry import PhotSettingsSchema, PhotometryDataSchema
from ..source_extraction import SourceExtractionDataSchema


__all__ = ['PhotometryJobResultSchema', 'PhotometryJobSchema']


class PhotometryJobResultSchema(JobResultSchema):
    data = List(Nested(PhotometryDataSchema),
                default=[])  # type: TList[PhotometryDataSchema]


class PhotometryJobSchema(JobSchema):
    result = Nested(
        PhotometryJobResultSchema,
        default={})  # type: PhotometryJobResultSchema
    file_ids = List(Integer(), default=[])  # type: TList[int]
    sources = List(
        Nested(SourceExtractionDataSchema),
        default=[])  # type: TList[SourceExtractionDataSchema]
    settings = Nested(
        PhotSettingsSchema, default={})  # type: PhotSettingsSchema
