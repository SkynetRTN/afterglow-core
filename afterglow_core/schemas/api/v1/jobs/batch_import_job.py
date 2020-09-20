"""
Afterglow Core: batch data file import job schemas
"""

from marshmallow.fields import String, Integer, List, Nested

from .... import AfterglowSchema, Boolean
from ..job import Job, JobResult


__all__ = [
    'BatchImportSettings', 'BatchImportJobResult', 'BatchImportJobSchema',
]


class BatchImportSettings(AfterglowSchema):
    provider_id = String()  # type: str
    path = String()  # type: str
    duplicates = String(default='ignore')  # type: str
    recurse = Boolean(default=False)  # type: bool


class BatchImportJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: list


class BatchImportJobSchema(Job):
    result = Nested(
        BatchImportJobResult, default={})  # type: BatchImportJobResult
    settings = List(
        Nested(BatchImportSettings, default={}), default=[])  # type: list
    session_id = Integer(default=None)  # type: int
