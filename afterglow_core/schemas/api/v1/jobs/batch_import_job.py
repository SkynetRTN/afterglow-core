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
    provider_id: str = String()
    path: str = String()
    duplicates: str = String(default='ignore')
    recurse: bool = Boolean(default=False)


class BatchImportJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), default=[])


class BatchImportJobSchema(JobSchema):
    type = 'batch_import'

    result: BatchImportJobResultSchema = Nested(
        BatchImportJobResultSchema, default={})
    settings: TList[BatchImportSettingsSchema] = List(Nested(
        BatchImportSettingsSchema, default={}), default=[])
    session_id: int = Integer(default=None)
