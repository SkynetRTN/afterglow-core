"""
Afterglow Core: batch data file import job plugin
"""

import json
from io import BytesIO
from typing import List as TList

from marshmallow.fields import String, Integer, List, Nested

from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean
from ...errors.data_provider import UnknownDataProviderError
from ...errors.data_file import CannotImportFromCollectionAssetError
from ..data_providers import providers
from ..data_files import get_data_file_db, get_root, import_data_file


__all__ = ['BatchImportJob']


class BatchImportSettings(AfterglowSchema):
    provider_id = String()  # type: str
    path = String()  # type: str
    duplicates = String(default='ignore')  # type: str
    recurse = Boolean(default=False)  # type: bool


class BatchImportJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: TList[int]


class BatchImportJob(Job):
    """
    Batch data file import job
    """
    type = 'batch_import'
    description = 'Batch Data File Import'

    result = Nested(
        BatchImportJobResult, default={})  # type: BatchImportJobResult
    settings = List(Nested(
        BatchImportSettings, default={}),
        default=[])  # type: TList[BatchImportSettings]
    session_id = Integer(default=None)  # type: int

    def run(self):
        adb = get_data_file_db(self.user_id)

        nfiles = len(self.settings)
        root = get_root(self.user_id)
        for i, settings in enumerate(self.settings):
            try:
                asset_path = settings.path

                try:
                    provider = providers[settings.provider_id]
                except KeyError:
                    raise UnknownDataProviderError(id=settings.provider_id)

                def recursive_import(path, depth=0):
                    asset = provider.get_asset(path)
                    if asset.collection:
                        if not provider.browseable:
                            raise CannotImportFromCollectionAssetError(
                                provider_id=provider.id, path=path)
                        if not settings.recurse and depth:
                            return []
                        return sum(
                            [recursive_import(child_asset.path, depth + 1)
                             for child_asset in provider.get_child_assets(
                                asset.path)], [])
                    return [f.id for f in import_data_file(
                        adb, root, provider.id, asset.path, asset.metadata,
                        BytesIO(provider.get_asset_data(asset.path)),
                        asset.name, settings.duplicates,
                        session_id=self.session_id)]

                if not isinstance(asset_path, list):
                    try:
                        asset_path = json.loads(asset_path)
                    except ValueError:
                        pass
                    if not isinstance(asset_path, list):
                        asset_path = [asset_path]

                self.result.file_ids += sum(
                    [recursive_import(p) for p in asset_path], [])
            except Exception as e:
                self.add_error('Data file #{}: {}'.format(i + 1, e))
            finally:
                self.state.progress = (i + 1)/nfiles*100
                self.update()

        if self.result.file_ids:
            adb.commit()
