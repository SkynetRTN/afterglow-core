"""
Afterglow Core: batch data file import job plugin
"""

import json
import time
from io import BytesIO
from typing import List as TList

from marshmallow.fields import String, Integer, List, Nested

from ...database import db
from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean
from ...errors.data_provider import UnknownDataProviderError
from ...errors.data_file import CannotImportFromCollectionAssetError
from .. import data_providers
from ..data_files import get_root, import_data_file


__all__ = ['BatchImportJob']


class BatchImportSettings(AfterglowSchema):
    provider_id: str = String()
    path: str = String()
    duplicates: str = String(dump_default='ignore')
    recurse: bool = Boolean(dump_default=False)


class BatchImportJobResult(JobResult):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class BatchImportJob(Job):
    """
    Batch data file import job
    """
    type = 'batch_import'
    description = 'Batch Data File Import'

    result: BatchImportJobResult = Nested(BatchImportJobResult, dump_default={})
    settings: TList[BatchImportSettings] = List(Nested(BatchImportSettings, dump_default={}), dump_default=[])
    session_id: int = Integer(dump_default=None)

    def run(self):
        try:
            nfiles = len(self.settings)
            root = get_root(self.user_id)
            for i, settings in enumerate(self.settings):
                try:
                    asset_path = settings.path

                    try:
                        provider = data_providers.providers[settings.provider_id]
                    except KeyError:
                        raise UnknownDataProviderError(id=settings.provider_id)

                    def recursive_import(path, depth=0):
                        asset = provider.get_asset(path)
                        if asset.collection:
                            if not provider.browseable:
                                raise CannotImportFromCollectionAssetError(provider_id=provider.id, path=path)
                            if not settings.recurse and depth:
                                return []
                            return sum(
                                [recursive_import(child_asset.path, depth + 1)
                                 for child_asset in provider.get_child_assets(asset.path)[0]], [])
                        return [f.id for f in import_data_file(
                            self.user_id, root, provider.id, asset.path, asset.metadata,
                            BytesIO(provider.get_asset_data(asset.path)),
                            asset.name, settings.duplicates, session_id=self.session_id)]

                    if not isinstance(asset_path, list):
                        try:
                            asset_path = json.loads(asset_path)
                        except ValueError:
                            pass
                        if not isinstance(asset_path, list):
                            asset_path = [asset_path]

                    self.result.file_ids += sum([recursive_import(p) for p in asset_path], [])
                except Exception as e:
                    self.add_error(e, {'file_no': i + 1})
                finally:
                    self.update_progress((i + 1)/nfiles*100)

            if self.result.file_ids:
                db.session.commit()
        except Exception:
            db.session.rollback()
            raise
