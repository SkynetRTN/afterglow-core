"""
Afterglow Core: data file and data provider asset batch download job plugins
"""

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from typing import List as TList

from marshmallow.fields import Integer, List, String

from ...models import Job
from ...errors import MissingFieldError, ValidationError
from ...errors.data_file import UnknownDataFileGroupError
from ...errors.data_provider import (
    NonBrowseableDataProviderError, UnknownDataProviderError)
from ..data_files import (
    get_data_file, get_data_file_bytes, get_data_file_group, get_data_file_path)
from ..data_providers import providers


__all__ = ['BatchDownloadJob', 'BatchAssetDownloadJob']


class BatchDownloadJob(Job):
    """
    Data file batch download job
    """
    type = 'batch_download'
    description = 'Download Multiple Data Files and Groups'

    file_ids: TList[int] = List(Integer(), default=[])
    group_ids: TList[str] = List(String(), default=[])

    def run(self):
        if not self.file_ids and not self.group_ids:
            raise ValidationError('file_ids|group_ids', 'Empty job')

        if len(self.file_ids) == 1 and not self.group_ids:
            # Single data file; don't create archive
            self.create_job_file(
                'download', get_data_file_bytes(self.user_id, self.file_ids[0]),
                mimetype='image/fits')
            return

        # Collect data files in groups
        groups = {}
        for file_id in self.file_ids:
            try:
                df = get_data_file(self.user_id, file_id)
                groups.setdefault(df.group_id, set()).add((file_id, df.name))
            except Exception as e:
                self.add_error('Data file ID {}: {}'.format(file_id, e))
        for group_id in self.group_ids:
            try:
                group = get_data_file_group(self.user_id, group_id)
                if not group:
                    raise UnknownDataFileGroupError(id=group_id)
                for df in group:
                    groups.setdefault(group_id, set()).add((df.id, df.name))
            except Exception as e:
                self.add_error('Data file group ID {}: {}'.format(group_id, e))

        # Ensure unique filenames within the archive
        file_id_lists, filenames = list(zip(
            *[([f[0] for f in list(files)], list(files)[0][1])
              for files in groups.values()]))
        for i, real_filename in enumerate(filenames):
            n = 1
            filename = real_filename
            while filename in filenames[:i] + filenames[i + 1:]:
                filename = real_filename + '.' + str(n)
                n += 1
            if filename != real_filename:
                filenames[i] = filename

        # Add single-file groups to the archive as individual files at top
        # level, multi-file groups as directories
        data = BytesIO()
        with ZipFile(data, 'w', ZIP_DEFLATED) as zf:
            for file_no, (file_ids, filename) in enumerate(
                    zip(file_id_lists, filenames)):
                if len(file_ids) == 1:
                    file_id = file_ids[0]
                    try:
                        zf.write(
                            get_data_file_path(self.user_id, file_id), filename)
                    except Exception as e:
                        self.add_error(
                            'Data file ID {} ({}): {}'.format(
                                file_id, filename, e))
                else:
                    for i, file_id in enumerate(file_ids):
                        try:
                            zf.write(
                                get_data_file_path(self.user_id, file_id),
                                filename + '/' + filename + '.' + str(i + 1))
                        except Exception as e:
                            self.add_error(
                                'Data file ID {} ({}): {}'.format(
                                    file_id, filename, e))

                self.update_progress((file_no + 1)/len(filenames)*100)

        self.create_job_file('download', data.getvalue(), 'application/zip')


class BatchAssetDownloadJob(Job):
    """
    Data provider asset batch download job
    """
    type = 'batch_asset_download'
    description = 'Download Multiple Data Provider Assets'

    provider_id: int = Integer(default=None)
    paths: TList[str] = List(String(), default=[])

    def run(self):
        if self.provider_id is None:
            raise MissingFieldError(field='provider_id')
        if not self.paths:
            raise ValidationError('paths', 'Empty job')

        try:
            provider = providers[self.provider_id]
        except KeyError:
            raise UnknownDataProviderError(id=self.provider_id)
        provider.check_auth()

        # Recursively retrieve all non-collection assets at the given paths
        assets = []

        def walk(asset_path, name=None):
            a = provider.get_asset(asset_path)
            if name is None:
                name = a.name
            if a.collection:
                if not provider.browseable:
                    raise NonBrowseableDataProviderError(id=provider.id)
                for child_asset in provider.get_child_assets(asset_path):
                    walk(child_asset.path, name + '/' + child_asset.name)
            else:
                assets.append((a, name))

        for path in set(self.paths):
            walk(path)

        if len(assets) == 1:
            # Single non-collection asset; don't create archive
            asset = assets[0][0]
            self.create_job_file(
                'download', provider.get_asset_data(asset.path),
                mimetype=asset.mimetype)
            return

        # Add asset to archive
        data = BytesIO()
        with ZipFile(data, 'w', ZIP_DEFLATED) as zf:
            for file_no, (asset, filename) in enumerate(assets):
                try:
                    zf.writestr(filename, provider.get_asset_data(asset.path))
                except Exception as e:
                    self.add_error(
                        'Asset "{}": {}'.format(asset.path, e))

                self.update_progress((file_no + 1)/len(assets)*100)

        self.create_job_file('download', data.getvalue(), 'application/zip')
