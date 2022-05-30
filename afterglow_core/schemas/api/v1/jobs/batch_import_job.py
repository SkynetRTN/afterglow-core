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
    duplicates: str = String(dump_default='ignore')
    recurse: bool = Boolean(dump_default=False)


class BatchImportJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class BatchImportJobSchema(JobSchema):
    type = 'batch_import'

    result: BatchImportJobResultSchema = Nested(
        BatchImportJobResultSchema, dump_default={})
    settings: TList[BatchImportSettingsSchema] = List(Nested(
        BatchImportSettingsSchema, dump_default={}), dump_default=[])
    session_id: int = Integer(dump_default=None)
