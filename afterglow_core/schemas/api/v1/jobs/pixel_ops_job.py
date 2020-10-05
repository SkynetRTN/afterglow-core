"""
Afterglow Core: pixel operations job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested, String

from .... import Boolean, Float
from ..job import JobSchema, JobResultSchema


__all__ = ['PixelOpsJobResultSchema', 'PixelOpsJobSchema']


class PixelOpsJobResultSchema(JobResultSchema):
    file_ids = List(Integer(), default=[])  # type: TList[int]
    data = List(Float(), default=[])  # type: TList[float]


class PixelOpsJobSchema(JobSchema):
    type = 'pixel_ops'

    result = Nested(PixelOpsJobResultSchema)  # type: PixelOpsJobResultSchema
    file_ids = List(Integer(), default=[])  # type: TList[int]
    op = String(default=None)  # type: str
    inplace = Boolean(default=False)  # type: bool
    aux_file_ids = List(Integer(), default=[])  # type: TList[int]
