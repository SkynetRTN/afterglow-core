"""
Afterglow Core: data file and data provider asset batch download job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, String

from ..job import JobSchema


__all__ = [
    'BatchDownloadJobSchema',
]


class BatchDownloadJobSchema(JobSchema):
    type = 'batch_download'

    file_ids: TList[int] = List(Integer(), dump_default=[])
    group_names: TList[str] = List(String(), dump_default=[])


class BatchAssetDownloadJobSchema(JobSchema):
    type = 'batch_asset_download'

    provider_id: int = Integer(dump_default=None)
    paths: TList[str] = List(String(), dump_default=[])
