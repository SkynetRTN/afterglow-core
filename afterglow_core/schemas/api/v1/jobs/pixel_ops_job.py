"""
Afterglow Core: pixel operations job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested, String

from .... import Boolean, Float
from ..job import JobSchema, JobResultSchema


__all__ = ['PixelOpsJobResultSchema', 'PixelOpsJobSchema']


class PixelOpsJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), dump_default=[])
    data: TList[float] = List(Float(), dump_default=[])


class PixelOpsJobSchema(JobSchema):
    type = 'pixel_ops'

    result: PixelOpsJobResultSchema = Nested(PixelOpsJobResultSchema)
    file_ids: TList[int] = List(Integer(), dump_default=[])
    op: str = String(dump_default=None)
    inplace: bool = Boolean(dump_default=False)
    aux_file_ids: TList[int] = List(Integer(), dump_default=[])
