"""
Afterglow Core: batch data file import job schemas
"""

from typing import List as TList

from marshmallow.fields import String, Integer, List, Nested

from .... import AfterglowSchema, Boolean
from ..job import JobSchema, JobResultSchema


__all__ = [
    'BatchImportSettingsSchema', 'BatchImportJobResultSchema',
    'BatchImportJobSchema',
]


class BatchImportSettingsSchema(AfterglowSchema):
    provider_id = String()  # type: str
    path = String()  # type: str
    duplicates = String(default='ignore')  # type: str
    recurse = Boolean(default=False)  # type: bool


class BatchImportJobResultSchema(JobResultSchema):
    file_ids = List(Integer(), default=[])  # type: TList[int]


class BatchImportJobSchema(JobSchema):
    type = 'batch_import'

    result = Nested(
        BatchImportJobResultSchema,
        default={})  # type: BatchImportJobResultSchema
    settings = List(Nested(
        BatchImportSettingsSchema, default={}),
        default=[])  # type: TList[BatchImportSettingsSchema]
    session_id = Integer(default=None)  # type: int
