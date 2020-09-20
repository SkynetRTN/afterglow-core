"""
Afterglow Core: local disk data provider plugin
"""

from __future__ import absolute_import, division, print_function
import sys
import os
import shutil
import gzip
import bz2
from errno import EEXIST
from datetime import datetime
from glob import glob

from marshmallow.fields import Boolean, String
import astropy.io.fits as pyfits

try:
    from PIL import Image as PILImage, ExifTags
except ImportError:
    PILImage = ExifTags = None

try:
    import rawpy
except ImportError:
    rawpy = None

try:
    import exifread
except ImportError:
    exifread = None

from ... import auth, errors
from ...schemas.api.v1 import DataProviderAsset
from ...errors.data_provider import (
    AssetNotFoundError, AssetAlreadyExistsError,
    CannotUpdateCollectionAssetError)
from ...errors.data_provider_local_disk import (
    AssetOutsideRootError, UnrecognizedDataFormatError, FilesystemError)
from . import DataProvider


__all__ = ['LocalDiskDataProvider']


class LocalDiskDataProvider(DataProvider):
    """
    Local disk data provider plugin class
    """
    name = 'local_disk'
    display_name = description = 'Local Filesystem'

    search_fields = dict(
        type=dict(label='Data File Type', type='multi_choice', enum=['FITS']),
        name=dict(label='File Name Pattern', type='text'),
        width=dict(label='Image Width', type='int', min_val=1),
        height=dict(label='Image Height', type='int', min_val=1),
    )
    if PILImage is not None:
        search_fields['type']['enum'] += ['JPEG', 'PNG', 'TIFF']
    if rawpy is not None:
        search_fields['type']['enum'].append('RAW')

    peruser = Boolean(default=False)
    root = String(default='.')

    @property
    def usage(self):
        """
        Return disk space usage

        :return: number of bytes within the data root directory
        :rtype: int
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.abs_root):
            for f in filenames:
                total_size += os.path.getsize(os.path.join(dirpath, f))
        return total_size

    @property
    def abs_root(self):
        """
        Return the absolute path to the local disk data provider root directory

        :return: local root directory path
        :rtype: str
        """
        p = os.path.abspath(os.path.expanduser(self.root))
        if self.peruser:
            user_id = auth.current_user.id
            if user_id:
                p = os.path.join(p, str(user_id))

                if not os.path.exists(p):
                    # In read-write per-user ("workspace") mode, make sure that
                    # the user workspace directory exists
                    try:
                        try:
                            os.makedirs(p)
                        except OSError as e:
                            if e.errno != EEXIST:
                                raise
                    except Exception as e:
                        # noinspection PyUnresolvedReferences
                        raise FilesystemError(
                            reason=e.message
                            if hasattr(e, 'message') and e.message
                            else ', '.join(str(arg) for arg in e.args) if e.args
                            else str(e))
        return p

    @staticmethod
    def _get_asset(path, filename):
        """
        Return an asset at the given path with no extra checks; used by
        other class methods and is not meant for external use

        :param str path: asset path
        :param str filename: full filesystem path to asset

        :return: asset object
        :rtype: DataProviderAsset
        """
        path = path.replace('\\', '/')
        name = os.path.basename(filename)

        if os.path.isdir(filename):
            # Collection asset
            return DataProviderAsset(
                name=name,
                collection=True,
                path=path,
                metadata=dict(
                    time=datetime.fromtimestamp(
                        os.stat(filename).st_mtime).isoformat(),
                )
            )

        # Asset is a file; try to read it and get metadata
        imtype = layers = imwidth = imheight = None
        explength = exptime = telescope = flt = None

        # A FITS file?
        # noinspection PyBroadException
        try:
            with pyfits.open(filename, 'readonly') as f:
                imtype = 'FITS'
                layers = len(f)
                imwidth = f[0].header['NAXIS1']
                imheight = f[0].header['NAXIS2']

                try:
                    explength = f[0].header['EXPOSURE']
                except KeyError:
                    pass

                try:
                    telescope = f[0].header['TELESCOP']
                except KeyError:
                    pass

                try:
                    flt = f[0].header['FILTER']
                except KeyError:
                    pass

                try:
                    try:
                        exptime = datetime.strptime(
                            f[0].header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S.%f')
                    except ValueError:
                        try:
                            exptime = datetime.strptime(
                                f[0].header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S')
                        except ValueError:
                            try:
                                exptime = datetime.strptime(
                                    f[0].header['DATE-OBS'] + 'T' +
                                    f[0].header['TIME-OBS'],
                                    '%Y-%m-%dT%H:%M:%S.%f')
                            except ValueError:
                                try:
                                    exptime = datetime.strptime(
                                        f[0].header['DATE-OBS'] + 'T' +
                                        f[0].header['TIME-OBS'],
                                        '%Y-%m-%dT%H:%M:%S')
                                except ValueError:
                                    pass
                except KeyError:
                    pass
        except Exception:
            pass

        if imtype is None and (PILImage is not None or rawpy is not None):
            with open(filename, 'rb') as f:
                exif = None

                if PILImage is not None:
                    from ..data_files import convert_exif_field
                    # noinspection PyBroadException
                    try:
                        with PILImage.open(f) as im:
                            imtype = im.format
                            layers = len(im.getbands())
                            imwidth, imheight = im.size
                            exif = {
                                ExifTags.TAGS[key]: convert_exif_field(val)
                                for key, val in getattr(im, '_getexif')()
                            }
                    except Exception:
                        pass

                if imtype is None and rawpy is not None:
                    # noinspection PyBroadException
                    try:
                        # Intercept stderr to disable rawpy warnings on non-raw
                        # files
                        save_stderr = sys.stderr
                        sys.stderr = os.devnull
                        try:
                            f.seek(0)
                            # noinspection PyTypeChecker
                            im = rawpy.imread(f)
                        finally:
                            sys.stderr = save_stderr
                        imtype = 'RAW'
                        layers = im.num_colors
                        imwidth = im.sizes.width
                        imheight = im.sizes.height
                    except Exception:
                        pass

                if imtype is not None and exifread is not None:
                    from ..data_files import convert_exif_field
                    # noinspection PyBroadException
                    try:
                        # Use ExifRead when available; remove "EXIF "
                        # etc. prefixes
                        f.seek(0)
                        exif = {
                            key.split(None, 1)[-1]: convert_exif_field(val)
                            for key, val in exifread.process_file(f).items()}
                    except Exception:
                        pass

                if exif is not None:
                    # Exposure length
                    # noinspection PyBroadException
                    try:
                        explength = exif['ExposureTime']
                    except Exception:
                        pass

                    # Exposure time
                    try:
                        exptime = exif['DateTime']
                    except KeyError:
                        try:
                            exptime = exif['DateTimeOriginal']
                        except KeyError:
                            try:
                                exptime = exif['DateTimeDigitized']
                            except KeyError:
                                pass
                    if exptime:
                        try:
                            exptime = datetime.strptime(
                                str(exptime), '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            try:
                                exptime = datetime.strptime(
                                    str(exptime),
                                    '%Y:%m:%d %H:%M:%S.%f')
                            except ValueError:
                                pass

        if imtype is None:
            # Unrecognized file
            raise UnrecognizedDataFormatError()

        stat = os.stat(filename)
        asset = DataProviderAsset(
            name=name,
            collection=False,
            path=path,
            metadata=dict(
                type=imtype,
                size=stat.st_size,
                time=(exptime if exptime is not None
                      else datetime.fromtimestamp(stat.st_mtime)).isoformat(),
                layers=layers,
                width=imwidth, height=imheight,
            ),
        )
        if explength is not None:
            asset.metadata['exposure'] = explength
        if telescope is not None:
            asset.metadata['telescope'] = telescope
        if flt is not None:
            asset.metadata['filter'] = flt

        return asset

    def get_asset(self, path):
        """
        Return an asset at the given path

        :param str path: asset path

        :return: asset object
        :rtype: DataProviderAsset
        """
        root = self.abs_root
        filename = os.path.abspath(os.path.join(root, path))

        # Prevent from going above the root path
        if not filename.startswith(root):
            raise AssetOutsideRootError()

        if not os.path.exists(filename):
            raise AssetNotFoundError(path=path)

        return self._get_asset(path, filename)

    def get_child_assets(self, path):
        """
        Return child assets of a collection asset at the given path

        :param str path: asset path; must identify a collection asset

        :return: list of :class:`DataProviderAsset` objects for child assets
        :rtype: list[DataProviderAsset]
        """
        root = self.abs_root
        filename = os.path.abspath(os.path.join(root, path))

        # Prevent from going above the root path
        if not filename.startswith(root):
            raise AssetOutsideRootError()

        if not os.path.isdir(filename):
            raise AssetNotFoundError(path=path)

        # Return directory contents
        return [DataProviderAsset(
            name=os.path.basename(fn),
            collection=os.path.isdir(fn),
            path=fn.split(root + os.path.sep)[1].replace('\\', '/'),
            metadata=dict(
                time=datetime.fromtimestamp(os.stat(fn).st_mtime).isoformat(),
            )
        ) for fn in glob(os.path.join(filename, '*'))]

    def find_assets(self, path=None, name=None, type=None, collection=None,
                    width=None, height=None):
        """
        Return a list of assets matching the given parameters

        :param str path: optional path to the collection asset to search in;
            by default, search in the data provider root
        :param str name: only return assets matching the given name; may include
            wildcards
        :param str type: comma-separated list of data types ("FITS", "JPEG",
            etc.); if specified, the query will match only data files of
            the given type(s)
        :param str collection: if specified, match only the given asset type
            (True | "1" = directories, False | "0" = files)
        :param str width: match only images of the given width
        :param str height: match only images of the given height

        :return: list of :class:`DataProviderAsset` objects for assets matching
            the search query parameters
        :rtype: list[DataProviderAsset]
        """
        # Set up filters
        if type:
            type = type.split(',')
        else:
            type = None
        if collection:
            try:
                collection = bool(int(collection))
            except ValueError:
                raise errors.ValidationError(
                    'collection', 'Collection flag must be 0 or 1')
        else:
            collection = None
        if width:
            try:
                width = int(width)
            except ValueError:
                raise errors.ValidationError('width', 'Width must be integer')
        else:
            width = None
        if height:
            try:
                height = int(height)
            except ValueError:
                raise errors.ValidationError('height', 'Height must be integer')
        else:
            height = None

        root = self.abs_root
        if path is None:
            # Search at the data root by default
            path = ''
            abs_path = root
        else:
            abs_path = os.path.abspath(os.path.join(root, path))

            # Prevent from going above the root path
            if not abs_path.startswith(root):
                raise AssetOutsideRootError()

        if not os.path.isdir(abs_path):
            raise AssetNotFoundError(path=path)

        # Look through all files within the path matching the given name
        assets = []
        if not name:
            name = '*'
        for filename in glob(os.path.join(abs_path, name)):
            if collection is not None and os.path.isdir(filename) != collection:
                # Fast path for searching collection or non-collection assets
                continue

            try:
                asset = self._get_asset(
                    filename.split(root + os.path.sep)[1], filename)
            except errors.AfterglowError:
                # Not a supported data file
                continue

            # Check other search filters
            if type is not None:
                try:
                    if asset.metadata['type'] not in type:
                        continue
                except KeyError:
                    continue

            if width is not None:
                try:
                    if asset.metadata['width'] != width:
                        continue
                except KeyError:
                    continue

            if height is not None:
                try:
                    if asset.metadata['height'] != height:
                        continue
                except KeyError:
                    continue

            # All checks passed
            assets.append(asset)

        return assets

    def get_asset_data(self, path):
        """
        Return data for a non-collection asset at the given path

        :param str path: asset path; must identify a non-collection asset

        :return: asset data
        :rtype: str
        """
        root = self.abs_root
        filename = os.path.abspath(os.path.join(root, path))

        # Prevent from going above the root path
        if not filename.startswith(root):
            raise AssetOutsideRootError()

        if not os.path.isfile(filename):
            raise AssetNotFoundError(path=path)

        # Return file contents
        try:
            if os.path.splitext(filename)[1] == '.gz':
                with gzip.GzipFile(filename, 'rb') as f:
                    return f.read()

            if os.path.splitext(filename)[1] == '.bz2':
                with bz2.BZ2File(filename, 'rb') as f:
                    return f.read()

            with open(filename, 'rb') as f:
                return f.read()
        except Exception as e:
            # noinspection PyUnresolvedReferences
            raise FilesystemError(
                reason=e.message if hasattr(e, 'message') and e.message
                else ', '.join(str(arg) for arg in e.args) if e.args
                else str(e))

    def create_asset(self, path, data=None, **kwargs):
        """
        Create an asset at the given path

        :param str path: path at which to create the asset
        :param bytes data: FITS image data; if omitted, create a collection
            asset

        :return: new data provider asset object
        :rtype: :class:`DataProviderAsset`
        """
        # Check that the given path does not exist
        root = self.abs_root
        filename = os.path.abspath(os.path.join(root, path))
        if not filename.startswith(root):
            raise AssetOutsideRootError()
        if os.path.exists(filename):
            raise AssetAlreadyExistsError()

        try:
            # Make sure that parent path exists
            d = os.path.dirname(filename)
            if not os.path.exists(d):
                try:
                    os.makedirs(d)
                except OSError as e:
                    if e.errno != EEXIST:
                        raise

            if data is None:
                # Create a collection asset
                os.makedirs(filename)
            else:
                # Save data to disk
                with open(filename, 'wb') as f:
                    f.write(data)

        except Exception as e:
            # noinspection PyUnresolvedReferences
            raise FilesystemError(
                reason=e.message if hasattr(e, 'message') and e.message
                else ', '.join(str(arg) for arg in e.args) if e.args
                else str(e))

        return self._get_asset(path, filename)

    def update_asset(self, path, data, **kwargs):
        """
        Update an asset at the given path

        :param str path: path of the asset to update
        :param bytes data: FITS file data

        :return: None
        """
        # Check that the given path exists and is not a directory
        root = self.abs_root
        filename = os.path.abspath(os.path.join(root, path))
        if not filename.startswith(root):
            raise AssetOutsideRootError()
        if not os.path.exists(filename):
            raise AssetNotFoundError(path=path)
        if os.path.isdir(filename):
            raise CannotUpdateCollectionAssetError()

        # Save data to disk overwriting existing file
        try:
            with open(filename, 'wb') as f:
                f.write(data)
        except Exception as e:
            # noinspection PyUnresolvedReferences
            raise FilesystemError(
                reason=e.message if hasattr(e, 'message') and e.message
                else ', '.join(str(arg) for arg in e.args) if e.args
                else str(e))

    def delete_asset(self, path, **kwargs):
        """
        Delete an asset at the given path

        :param str path: path of the asset to delete

        :return: None
        """
        # Check that the given path exists
        root = self.abs_root
        filename = os.path.abspath(os.path.join(root, path))
        if not filename.startswith(root):
            raise AssetOutsideRootError()
        if not os.path.exists(filename):
            raise AssetNotFoundError(path=path)

        if os.path.isdir(filename):
            try:
                shutil.rmtree(filename)
            except Exception as e:
                # noinspection PyUnresolvedReferences
                raise FilesystemError(
                    reason=e.message if hasattr(e, 'message') and e.message
                    else ', '.join(str(arg) for arg in e.args) if e.args
                    else str(e))
        else:
            try:
                os.remove(filename)
            except Exception as e:
                # noinspection PyUnresolvedReferences
                raise FilesystemError(
                    reason=e.message if hasattr(e, 'message') and e.message
                    else ', '.join(str(arg) for arg in e.args) if e.args
                    else str(e))
