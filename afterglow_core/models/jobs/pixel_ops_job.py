"""
Afterglow Core: pixel operations job schemas
"""

from marshmallow.fields import Integer, List, Nested, String

from .. import Boolean, Float
from . import Job, JobResult


__all__ = ['PixelOpsJobResult', 'PixelOpsJobSchema']


class PixelOpsJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: list
    data = List(Float(), default=[])  # type: list


class PixelOpsJobSchema(Job):
    result = Nested(PixelOpsJobResult)  # type: PixelOpsJobResult
    file_ids = List(Integer(), default=[])  # type: list
    op = String(default=None)  # type: str
    inplace = Boolean(default=False)  # type: bool
    aux_file_ids = List(Integer(), default=[])  # type: list
