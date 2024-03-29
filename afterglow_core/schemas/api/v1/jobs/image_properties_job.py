"""
Afterglow Core: image property extraction job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested

from ..job import JobSchema, JobResultSchema
from ..image_properties import ImagePropertiesSchema
from .source_extraction_job import SourceExtractionSettingsSchema


__all__ = ['ImagePropsExtractionJobResultSchema',
           'ImagePropsExtractionJobSchema']


class ImagePropsExtractionJobResultSchema(JobResultSchema):
    data: TList[ImagePropertiesSchema] = List(
        Nested(ImagePropertiesSchema), dump_default=[])


class ImagePropsExtractionJobSchema(JobSchema):
    type = 'image_props'

    result: ImagePropsExtractionJobResultSchema = Nested(
        ImagePropsExtractionJobResultSchema, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    source_extraction_settings: SourceExtractionSettingsSchema = Nested(
        SourceExtractionSettingsSchema, dump_default=None)
