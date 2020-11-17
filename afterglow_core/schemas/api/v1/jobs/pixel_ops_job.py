"""
Afterglow Core: pixel operations job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested, String

from .... import Boolean, Float
from ..job import JobSchema, JobResultSchema


__all__ = ['PixelOpsJobResultSchema', 'PixelOpsJobSchema']


class PixelOpsJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), default=[])
    data: TList[float] = List(Float(), default=[])


class PixelOpsJobSchema(JobSchema):
    type = 'pixel_ops'

    result: PixelOpsJobResultSchema = Nested(PixelOpsJobResultSchema)
    file_ids: TList[int] = List(Integer(), default=[])
    op: str = String(default=None)
    inplace: bool = Boolean(default=False)
    aux_file_ids: TList[int] = List(Integer(), default=[])
