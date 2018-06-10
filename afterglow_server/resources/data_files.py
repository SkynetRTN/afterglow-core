"""
Afterglow Access Server: data-files resource
"""

from __future__ import absolute_import, division, print_function
import sys
import os
from glob import glob
from datetime import datetime
import json
import gzip
import tempfile
import shutil
import subprocess
from threading import Lock
from io import BytesIO

from marshmallow import fields
from sqlalchemy import Column, DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import numpy
import astropy.io.fits as pyfits
from flask import Response, request

from skylib.calibration.background import estimate_background
from skylib.sonification import sonify_image

from . import data_providers
from .. import Resource, app, errors, json_response, url_prefix
from ..auth import auth_required, current_user

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


__all__ = [
    'UnknownDataFileError', 'CannotCreateDataFileDirError',
    'CannotImportFromCollectionAssetError', 'UnrecognizedDataFileError',
    'MissingWCSError', 'DataFile', 'SqlaDataFile',
    'data_files_engine', 'data_files_engine_lock',
    'save_data_file', 'create_data_file', 'get_data_file', 'get_data_file_data',
    'get_data_file_db', 'get_data_file_path', 'get_exp_length', 'get_gain',
    'get_image_time', 'get_phot_cal', 'get_root', 'get_subframe',
    'convert_exif_field',
]


class UnknownDataFileError(errors.AfterglowError):
    """
    Format of the data file being imported is not recognized

    Extra attributes::
        id: requested data file ID
    """
    code = 404
    subcode = 2000
    message = 'Unknown data file ID'


class CannotCreateDataFileDirError(errors.AfterglowError):
    """
    Initializing the user data file storage failed (e.g. directory not
    writeable or database creation error)

    Extra attributes::
        reason: error message describing the reason why the operation has failed
    """
    code = 403
    subcode = 2001
    message = 'Cannot create data file storage directory'


class CannotImportFromCollectionAssetError(errors.AfterglowError):
    """
    An attempt was made to import a data file from a collection asset

    Extra attributes::
        provider_id: data provider ID
        path: requested asset path
    """
    code = 403
    subcode = 2002
    message = 'Cannot import from collection asset'


class UnrecognizedDataFileError(errors.AfterglowError):
    """
    An attempt was made to import a data file that has unknown format

    Extra attributes::
        none
    """
    code = 403
    subcode = 2003
    message = 'Data file format not recognized'


class MissingWCSError(errors.AfterglowError):
    """
    Data file has now WCS calibration

    Extra attributes::
        none
    """
    code = 400
    subcode = 2004
    message = 'Missing WCS info'


class DataFile(Resource):
    """
    JSON-serializable data file class

    Attributes::
        id: unique integer data file ID; assigned automatically when creating
            or importing the data file
        name: data file name; on import, set to the data provider asset name
        width: image width
        height: image height
        data_provider: for imported data files, name of the originating data
            provider; not defined for data files created from scratch or
            uploaded
        asset_path: for imported data files, the original asset path
        asset_metadata: dictionary of the originating data provider asset
            metadata
        layer: layer ID for data files imported from multi-layer data provider
            assets
        created_on: datetime.datetime of data file creation
    """
    __get_view__ = 'data_files'

    id = fields.Integer(default=None)
    type = fields.String(default=None)
    name = fields.String(default=None)
    width = fields.Integer(default=None)
    height = fields.Integer(default=None)
    data_provider = fields.String(default=None)
    asset_path = fields.String(default=None)
    asset_metadata = fields.Dict(default={})
    layer = fields.String(default=None)
    created_on = fields.DateTime(default=None, format='%Y-%m-%d %H:%M:%S')

    def __init__(self, _obj=None, **kwargs):
        """
        Create a new data file

        :param :class:`SqlaDataFile` _obj: SQLA data file returned by database
            query
        :param kwargs: if `_obj` is not set, initialize the data file fields
            from the given keyword=value pairs
        """
        # Extract fields from SQLA object
        kw = {name: getattr(_obj, name) for name in self._declared_fields
              if name not in getattr(Resource, '_declared_fields')}
        kw.update(kwargs)

        # Convert fields stored as strings in the db to their proper schema
        # types
        if kw.get('asset_metadata') is not None:
            kw['asset_metadata'] = json.loads(kw['asset_metadata'])

        super(DataFile, self).__init__(**kw)


Base = declarative_base()


# noinspection PyClassHasNoInit
class SqlaDataFile(Base):
    __tablename__ = 'data_files'

    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(String)
    name = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    data_provider = Column(String)
    asset_path = Column(String)
    asset_metadata = Column(String)
    layer = Column(String)
    created_on = Column(DateTime, default=func.now())


def get_root(user_id):
    """
    Return the absolute path to the current authenticated user's data storage
    root directory

    :param int | None user_id: current user ID (None if user auth is disabled)

    :return: user's data storage path
    :rtype: str
    """
    root = app.config['DATA_FILE_ROOT']
    if user_id:
        root = os.path.join(root, str(user_id))
    return os.path.abspath(os.path.expanduser(root))


# SQLA database engine
data_files_engine = {}
data_files_engine_lock = Lock()


def get_data_file_db(user_id):
    """
    Initialize the given user's data file storage directory and database as
    needed and return the database object

    This function should be used instead of directly accessing the global
    `adb` variable to ensure thread safety

    :param int | None user_id: current user ID (None if user auth is disabled)

    :return: SQLAlchemy session object
    :rtype: sqlalchemy.orm.session.Session
    """
    try:
        root = get_root(user_id)

        # Make sure the user's data directory exists
        if os.path.isfile(root):
            os.remove(root)
        if not os.path.isdir(root):
            os.makedirs(root)

        with data_files_engine_lock:
            try:
                # Get engine from cache
                engine = data_files_engine[root]
            except KeyError:
                # Engine does not exist, create it
                engine = data_files_engine[root] = create_engine(
                    'sqlite:///{}'.format(os.path.join(root, 'data_files.db')))

                # Create table
                Base.metadata.create_all(bind=engine)

            return scoped_session(sessionmaker(bind=engine))()

    except Exception as e:
        raise CannotCreateDataFileDirError(
            reason=e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e))


def save_data_file(root, file_id, data, hdr):
    """
    Save data file to the user's data file directory as an single (image) or
    double (image + mask) HDU FITS or a primary + table HDU FITS, depending on
    whether the input HDU contains an image or a table

    :param str root: user's data file storage root directory
    :param int file_id: data file ID
    :param array_like data: image or table data; image data can be a masked
        array
    :param astropy.io.fits.Header hdr: FITS header

    :return: None
    """
    # Convert image data to float32
    if data.dtype.fields is None:
        data = data.astype(numpy.float32)
        if isinstance(data, numpy.ma.MaskedArray) and data.mask.any():
            # Store masked array in two HDUs
            fits = pyfits.HDUList(
                [pyfits.PrimaryHDU(data.data, hdr),
                 pyfits.ImageHDU(data.mask, name='MASK')])
        else:
            fits = pyfits.PrimaryHDU(data.data, hdr)
    else:
        # Treat normal arrays with NaN's as masked arrays
        mask = numpy.isnan(data)
        if mask.any():
            fits = pyfits.HDUList(
                [pyfits.PrimaryHDU(data, hdr),
                 pyfits.ImageHDU(mask, name='MASK')])
        else:
            fits = pyfits.BinTableHDU(data, hdr)

    # Save FITS to data file directory
    fits.writeto(
        os.path.join(root, '{}.fits'.format(file_id)),
        'silentfix', overwrite=True)


def create_data_file(adb, name, root, data, hdr=None, provider=None, path=None,
                     metadata=None, layer=None, duplicates='ignore'):
    """
    Create a database entry for a new data file and save it to data file
    directory as an single (image) or double (image + mask) HDU FITS or
    a primary + table HDU FITS, depending on whether the input HDU contains
    an image or a table

    :param sqlalchemy.orm.session.Session adb: SQLA database session
    :param str | None name: data file name
    :param str root: user's data file storage root directory
    :param array_like data: image or table data; image data can be a masked
        array
    :param astropy.io.fits.Header | None hdr: FITS header
    :param str provider: data provider ID/name if not creating an empty data
        file
    :param str path: path of the data provider asset the file was imported from
    :param dict metadata: data provider asset metadata
    :param str layer: optional layer ID for multiple-layer assets
    :param str duplicates: optional duplicate handling mode used if the data
        file with the same `provider`, `path`, and `layer` was already imported
        before: "ignore" (default) = don't re-import the existing data file,
        "overwrite" = re-import the file and replace the existing data file,
        "append" = always import as a new data file

    :return: data file instance
    :rtype: DataFile
    """
    if data.dtype.fields is None:
        # Image HDU; get image dimensions from array shape
        height, width = data.shape
    else:
        # Table HDU; width = number of columns, height = number of rows
        height, width = len(data), len(data.dtype.fields)

    if not name:
        name = datetime.utcnow().isoformat('_'). \
            replace('-', '').replace(':', '')
        try:
            name = name[:name.index('.')]
        except ValueError:
            pass
        name = 'file_{}'.format(name)

    # Create/update a database row
    sqla_fields = dict(
        type='image' if data.dtype.fields is None else 'table',
        name=name,
        width=width,
        height=height,
        data_provider=provider,
        asset_path=path,
        asset_metadata=json.dumps(metadata) if metadata is not None else None,
        layer=layer,
    )

    if duplicates in ('ignore', 'overwrite'):
        # Look for an existing data file with the same import parameters
        sqla_data_file = adb.query(SqlaDataFile).filter_by(
            data_provider=provider, asset_path=path, layer=layer,
        ).one_or_none()

        if sqla_data_file is not None:
            if duplicates == 'ignore':
                # Don't reimport existing data files
                return DataFile(sqla_data_file)

            # Overwrite existing data file
            for attr, val in sqla_fields.items():
                setattr(sqla_data_file, attr, val)
    else:
        sqla_data_file = None

    if sqla_data_file is None:
        # Add a database row and obtain its ID
        sqla_data_file = SqlaDataFile(**sqla_fields)
        adb.add(sqla_data_file)
        adb.flush()  # obtain the new row ID by flushing db

    save_data_file(root, sqla_data_file.id, data, hdr)

    return DataFile(sqla_data_file)


def import_data_file(adb, root, provider_id, asset_path, asset_metadata, fp,
                     name, duplicates='ignore'):
    """
    Create data file(s) from a (possibly multi-layer) non-collection data
    provider asset or from an uploaded file

    :param sqlalchemy.orm.session.Session adb: SQLA database session
    :param str root: user's data file storage root directory
    :param str | None provider_id: data provider ID/name
    :param str | None asset_path: data provider asset path
    :param dict asset_metadata: data provider asset metadata
    :param fp: file-like object containing the asset data, should be opened for
        reading
    :param str | None name: data file name
    :param str duplicates: optional duplicate handling mode used if the data
        file with the same `provider`, `path`, and `layer` was already imported
        before: "ignore" (default) = don't re-import the existing data file,
        "overwrite" = re-import the file and replace the existing data file,
        "append" = always import as a new data file

    :return: list of DataFile instances created/updated
    :rtype: list[DataFile]
    """
    all_data_files = []

    # A FITS file?
    # noinspection PyBroadException
    try:
        fp.seek(0)
        with pyfits.open(fp, 'readonly') as fits:
            # Store non-default primary HDU header cards to copy them to all
            # FITS files for separate extension HDUs
            primary_header = fits[0].header.copy()
            for kw in ('SIMPLE', 'BITPIX', 'NAXIS', 'EXTEND', 'CHECKSUM',
                       'DATASUM'):
                try:
                    del primary_header[kw]
                except KeyError:
                    pass

            # Import each HDU as a separate data file
            for i, hdu in enumerate(fits):
                if isinstance(hdu, pyfits.ImageHDU.__base__):
                    # Image HDU; eliminate redundant extra dimensions if any,
                    # skip non-2D images
                    imshape = hdu.shape
                    if len(imshape) < 2 or len(imshape) > 2 and \
                            len([d for d in imshape if d != 1]) != 2 or \
                            any(not d for d in imshape):
                        continue
                    if len(imshape) > 2:
                        # Eliminate extra dimensions
                        imshape = tuple([d for d in imshape if d != 1])
                        hdu.header['NAXIS'] = 2
                        hdu.header['NAXIS2'], hdu.header['NAXIS1'] = imshape
                        hdu.data = hdu.data.reshape(imshape)

                if name and len(fits) > 1 + int(
                        isinstance(hdu, pyfits.TableHDU.__base__)):
                    # When importing multiple HDUs, append a unique suffix to
                    # DataFile.name (e.g. filter name)
                    layer = hdu.header.get('FILTER')
                    if not layer:
                        # No channel name; use number
                        layer = str(i + 1)
                    fullname = name + '.' + layer
                else:
                    layer = None
                    fullname = name

                if i and primary_header:
                    # Copy primary header cards to extension header
                    h = primary_header.copy()
                    for kw in hdu.header:
                        if kw not in ('COMMENT', 'HISTORY'):
                            try:
                                del h[kw]
                            except KeyError:
                                pass
                    hdu.header.update(h)

                all_data_files.append(create_data_file(
                    adb, fullname, root, hdu.data, hdu.header, provider_id,
                    asset_path, asset_metadata, layer, duplicates))

    except errors.AfterglowError:
        raise
    except Exception:
        # Non-FITS file; try importing all color planes with Pillow and rawpy
        exif = None
        channels = {}

        if PILImage is not None:
            # noinspection PyBroadException
            try:
                fp.seek(0)
                with PILImage.open(fp) as im:
                    width, height = im.size
                    band_names = im.getbands()
                    if len(band_names) > 1:
                        bands = im.split()
                    else:
                        bands = (im,)
                    channels = {
                        band_name: numpy.fromstring(
                            band.tobytes(), numpy.uint8).reshape(
                            [height, width])
                        for band_name, band in zip(band_names, bands)}
                    if exifread is None:
                        exif = {
                            ExifTags.TAGS[key]: convert_exif_field(val)
                            for key, val in getattr(im, '_getexif')()
                        }
            except Exception:
                pass

        if not channels and rawpy is not None:
            # noinspection PyBroadException
            try:
                # Intercept stderr to disable rawpy warnings on non-raw files
                save_stderr = sys.stderr
                sys.stderr = os.devnull
                try:
                    fp.seek(0)
                    im = rawpy.imread(fp)
                finally:
                    sys.stderr = save_stderr
                r, g, b = numpy.rollaxis(im.postprocess(output_bps=16), 2)
                channels = {'R': r, 'G': g, 'B': b}
            except Exception:
                pass

        if channels and exifread is not None:
            # noinspection PyBroadException
            try:
                # Use ExifRead when available; remove "EXIF " etc. prefixes
                fp.seek(0)
                exif = {
                    key.split(None, 1)[-1]: convert_exif_field(val)
                    for key, val in exifread.process_file(fp).items()}
            except Exception:
                pass

        hdr = pyfits.Header()
        if exif is not None:
            # Exposure length
            # noinspection PyBroadException
            try:
                hdr['EXPOSURE'] = (exif['ExposureTime'], '[s] Integration time')
            except Exception:
                pass

            # Exposure time
            try:
                t = exif['DateTime']
            except KeyError:
                try:
                    t = exif['DateTimeOriginal']
                except KeyError:
                    try:
                        t = exif['DateTimeDigitized']
                    except KeyError:
                        t = None
            if t:
                try:
                    t = datetime.strptime(str(t), '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    try:
                        t = datetime.strptime(str(t), '%Y:%m:%d %H:%M:%S.%f')
                    except ValueError:
                        t = None
            if t:
                hdr['DATE-OBS'] = (
                    t.isoformat(),
                    'UTC date/time of exposure start')

            # Focal length
            # noinspection PyBroadException
            try:
                hdr['FOCLEN'] = (exif['FocalLength'],
                                 '[mm] Effective focal length')
            except Exception:
                pass

            # Pixel size
            # noinspection PyBroadException
            try:
                hdr['XPIXSZ'] = (
                    25.4/exif['FocalPlaneXResolution'],
                    '[mm] Horizontal pixel size')
            except Exception:
                pass
            # noinspection PyBroadException
            try:
                hdr['YPIXSZ'] = (
                    25.4/exif['FocalPlaneYResolution'],
                    '[mm] Vertical pixel size')
            except Exception:
                pass

        for channel, data in channels.items():
            if channel:
                hdr['FILTER'] = (channel, 'Filter name')

            if name and len(channels) > 1 and channel:
                layer = channel
                fullname = name + '.' + channel
            else:
                layer = None
                fullname = name

            # Store FITS image bottom to top
            all_data_files.append(create_data_file(
                adb, fullname, root, data[::-1], hdr, provider_id, asset_path,
                asset_metadata, layer, duplicates))

    return all_data_files


def convert_exif_field(val):
    """
    Convert EXIF field to standard Python type

    :param val: EXIF field from either ExifRead or PIL

    :return: normalized field value
    """
    if hasattr(val, 'values'):
        # Multiple-item ExifRead value
        val = val.values
        if val and hasattr(val, '__getitem__') and \
                not isinstance(val, str) and not isinstance(val, unicode):
            val = val[0]

    if isinstance(val, tuple) and len(val) == 2:
        # PIL ratio
        return val[0]/val[1]

    if hasattr(val, 'num') and hasattr(val, 'den'):
        # ExifRead ratio
        if val.den:
            return val.num/val.den
        return val.num

    # Otherwise, return as string
    return str(val)


def get_subframe(user_id, file_id, x0=None, y0=None, w=None, h=None):
    """
    Return pixel data for the given image data file ID within a rectangle
    defined by the optional request parameters "x", "y", "width", and "height";
    XY are in the FITS system with (1,1) at the bottom left corner of the image

    :param int | None user_id: current user ID (None if user auth is disabled)
    :param int file_id: data file ID
    :param int x0: optional subframe origin X coordinate (1-based)
    :param int y0: optional subframe origin Y coordinate (1-based)
    :param int w: optional subframe width
    :param int h: optional subframe height

    :return: NumPy float32 array containing image data within the specified
        region
    :rtype: `numpy.ndarray`
    """
    data = get_data_file(user_id, file_id)[0]
    is_image = data.dtype.fields is None
    if is_image:
        height, width = data.shape
    else:
        # FITS table
        width = len(data.dtype.fields)
        height = len(data)

    if x0 is None:
        x0 = request.args.get('x', 1)
    try:
        x0 = int(x0) - 1
        if x0 < 0 or x0 >= width:
            raise errors.ValidationError(
                'x', 'X must be positive and not greater than image width', 422)
    except ValueError:
        raise errors.ValidationError('x', 'X must be a positive integer')

    if y0 is None:
        y0 = request.args.get('y', 1)
    try:
        y0 = int(y0) - 1
        if y0 < 0 or y0 >= height:
            raise errors.ValidationError(
                'y', 'Y must be positive and not greater than image height',
                422)
    except ValueError:
        raise errors.ValidationError('y', 'Y must be a positive integer')

    if w is None:
        w = request.args.get('width', width - x0)
    elif not w:
        w = width - x0
    try:
        w = int(w)
        if w <= 0 or w > width - x0:
            raise errors.ValidationError(
                'width',
                'Width must be positive and less than or equal to {:d}'.format(
                    width - x0), 422)
    except ValueError:
        raise errors.ValidationError(
            'width', 'Width must be a positive integer')

    if h is None:
        h = request.args.get('height', height - y0)
    elif not h:
        h = height - y0
    try:
        h = int(h)
        if h <= 0 or h > height - y0:
            raise errors.ValidationError(
                'height',
                'Height must be positive and less than or equal to {:d}'.format(
                    height - y0), 422)
    except ValueError:
        raise errors.ValidationError(
            'height', 'Height must be a positive integer')

    if is_image:
        return data[y0:y0+h, x0:x0+w]

    # For tables, convert Astropy FITS table to NumPy structured array and
    # extract the required range of columns, then the required range of rows
    data = numpy.array(data)
    return data[list(data.dtype.names[x0:x0+w])][y0:y0+h]


def get_data_file_path(user_id, file_id):
    """
    Return data file path on disk

    :param int | None user_id: current user ID (None if user auth is disabled)
    :param int file_id: data file ID

    :return: path to data file
    :rtype: str
    """
    return os.path.join(get_root(user_id), '{}.fits'.format(file_id))


def get_data_file(user_id, file_id):
    """
    Return FITS file data and header for a data file with the given ID; handles
    masked images

    :param int | None user_id: current user ID (None if user auth is disabled)
    :param int file_id: data file ID

    :return: tuple (data, hdr); if the underlying FITS file contains a mask in
        an extra image HDU, it is converted into a :class:`numpy.ma.MaskedArray`
        instance
    :rtype: tuple(array_like, astropy.io.fits.Header)
    """
    try:
        fits = pyfits.open(get_data_file_path(user_id, file_id), 'readonly')
    except Exception:
        raise UnknownDataFileError(id=file_id)

    if fits[0].data is None:
        # Table stored in extension HDU
        data = fits[1].data
    elif fits[0].data.dtype.fields is None:
        # Image stored in the primary HDU, with an optional mask
        if len(fits) == 1:
            # Normal image data
            data = fits[0].data
        else:
            # Masked data
            data = numpy.ma.MaskedArray(fits[0].data, fits[1].data)
    else:
        # Table data in the primary HDU (?)
        data = fits[0].data

    return data, fits[0].header


def get_data_file_data(user_id, file_id):
    """
    Return FITS file data for data file with the given ID

    :param int | None user_id: current user ID (None if user auth is disabled)
    :param int file_id: data file ID

    :return: data file bytes
    :rtype: bytes
    """
    try:
        with open(get_data_file_path(user_id, file_id), 'rb') as f:
            return f.read()
    except Exception:
        raise UnknownDataFileError(id=file_id)


def get_image_time(hdr):
    """
    Get exposure start time from FITS header

    :param astropy.io.fits.Header hdr: FITS file header

    :return: exposure start time; None if unknown
    :rtype: datetime.datetime | None
    """
    try:
        dateobs = hdr['DATE-OBS']
    except KeyError:
        raise Exception('Unable to determine image time.  '
                        'Key DATE-OBS must be present')

    # check if time is also in date by looking for 'T'
    if 'T' not in dateobs:
        try:
            timeobs = hdr['TIME-OBS']
        except KeyError:
            return None
        else:
            # Normalize to standard format
            dateobs += 'T' + timeobs

    try:
        return datetime.strptime(dateobs, '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        try:
            return datetime.strptime(dateobs, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            return None


def get_exp_length(hdr):
    """
    Get exposure length from FITS header

    :param `astropy.io.fits.Header` hdr: FITS file header

    :return: exposure length in seconds; None if unknown
    :rtype: float
    """
    # noinspection PyUnusedLocal
    texp = None
    for name in ('EXPOSURE', 'EXPTIME'):
        try:
            texp = float(hdr[name])
        except (KeyError, ValueError):
            continue
        else:
            break
    return texp


def get_gain(hdr):
    """
    Get effective gain from FITS header

    :param `astropy.io.fits.Header` hdr: FITS file header

    :return: effective gain in e-/ADU; None if unknown
    :rtype: float
    """
    # noinspection PyUnusedLocal
    gain = None
    for name in ('GAIN', 'EGAIN', 'EPERADU'):
        try:
            gain = float(hdr[name])
        except (KeyError, ValueError):
            continue
        else:
            break
    return gain


def get_phot_cal(hdr):
    """
    Get photometric calibration from FITS header

    :param `astropy.io.fits.Header` hdr: FITS file header

    :return: dictionary with photometric calibration parameters
    :rtype: dict
    """
    params = {}

    try:
        params['m0'] = float(hdr['PHOT_M0'])
    except (KeyError, ValueError):
        pass

    try:
        params['m0_err'] = float(hdr['PHOT_M0E'])
    except (KeyError, ValueError):
        pass

    return params


def make_data_response(data, status_code=200):
    """
    Initialize a Flask response object returning the binary data array

    Depending on the request headers (Accept and Accept-Encoding), the data are
    returned either as an optionally gzipped binary stream or as a JSON list.

    :param bytes | array_like data: data to send to the client
    :param int status_code: optional HTTP status code; defaults to 200 - OK

    :return: Flask response object
    :rtype: flask.Response
    """
    # Figure out how to transfer pixel data to the client
    is_array = isinstance(data, numpy.ndarray)
    accepted_mimetypes = request.headers['Accept']
    if accepted_mimetypes:
        allow_json = allow_bin = False
        for mt in accepted_mimetypes.split(','):
            mtype, subtype = mt.split(';')[0].strip().lower().split('/')
            if mtype in ('application', '*'):
                if subtype == 'json' and is_array:
                    allow_json = True
                elif subtype == 'octet-stream':
                    allow_bin = True
                elif subtype == '*':
                    allow_json = is_array
                    allow_bin = True
    else:
        # Accept header not specified, assume all types are allowed
        allow_json = is_array
        allow_bin = True

    allow_gzip = False
    # accepted_encodings = request.headers['Accept-Encoding']
    # if accepted_encodings is not None:
    #     for enc in accepted_encodings.split(','):
    #         if enc.split(';')[0].strip().lower() == 'gzip':
    #             allow_gzip = True

    if allow_bin:
        if is_array:
            # Make sure data are in little-endian byte order before sending over
            # the net
            if data.dtype.byteorder == '>' or \
                    data.dtype.byteorder == '=' and sys.byteorder == 'big':
                data = data.byteswap()
            data = data.tobytes()
            mimetype = 'application/octet-stream'
        else:
            # Sending FITS file
            mimetype = 'image/fits'
        if allow_gzip:
            s = BytesIO()
            with gzip.GzipFile(fileobj=s, mode='wb') as f:
                f.write(data)
            data = s.getvalue()
            headers = [('Content-Encoding', 'gzip')]
        else:
            headers = None
        return Response(data, status_code, headers, mimetype)

    if allow_json and is_array:
        return json_response(data.tolist(), status_code)

    # Could not send data in any of the formats supported by the client
    raise errors.NotAcceptedError(accepted_mimetypes=accepted_mimetypes)


resource_prefix = url_prefix + 'data-files/'


@app.route(resource_prefix[:-1], methods=['GET', 'POST'])
@app.route(resource_prefix + '<int:id>', methods=['GET', 'PUT', 'DELETE'])
@auth_required('user')
def data_files(id=None):
    """
    Return, create, update, or delete data file(s)

    GET /data-files
        - return a list of all user's data files

    GET /data-files/[id]
        - return a single data file with the given ID

    POST /data-files?name=...&width=...&height=...&pixel_value=...
        - create a single data file of the given width and height, with data
          values set to pixel_value (0 by default)

    POST /data-files?name=...
        - import data file from the request body

    POST /data-files?provider_id=...&path=...&duplicates=...&recurse=...
        - import file(s) from a data provider asset at the given path; if the
          path identifies a collection asset of a browseable data provider,
          import all non-collection child assets (and, optionally, all
          collection assets too if recurse=1); the `duplicates` argument defines
          the import behavior in the case when a certain non-collection asset
          was already imported: "ignore" (default) = skip already imported
          assets, "overwrite" = re-import, "append" = always create a new data
          file; multiple asset paths can be passed as a JSON list

    PUT /data-files/[id]?name=...
        - rename data file

    DELETE /data-files/[id]
        - delete the given data file

    :param int id: data file ID for GET and DELETE requests

    :return:
        GET: JSON response containing either the list of serialized data file
            objects when no id supplied or a single data file otherwise
        POST: JSON-serialized list of the new data files
        DELETE: empty response
    :rtype: flask.Response | str
    """
    root = get_root(current_user.id)
    adb = get_data_file_db(current_user.id)

    if id is not None:
        # When getting, updating, or deleting a data file, check that it
        # exists
        data_file = adb.query(SqlaDataFile).get(id)
        if data_file is None:
            raise UnknownDataFileError(id=id)
    else:
        data_file = None

    if request.method == 'GET':
        if id is None:
            # List all data files
            return json_response(
                [DataFile(data_file) for data_file in adb.query(SqlaDataFile)])

        # Return specific data file resource
        return json_response(DataFile(data_file))

    if request.method == 'POST':
        # Create data file(s)
        all_data_files = []

        try:
            if request.args.get('provider_id') is None and \
                    request.args.get('width') is not None and \
                    request.args.get('height') is not None:
                # Create an empty image data file
                name = request.args.get('name')
                try:
                    width = int(request.args['width'])
                    if width < 1:
                        raise errors.ValidationError(
                            'width', 'Width must be positive', 422)
                except ValueError:
                    raise errors.ValidationError(
                        'width', 'Width must be a positive integer')
                try:
                    height = int(request.args['height'])
                    if height < 1:
                        raise errors.ValidationError(
                            'height', 'Height must be positive', 422)
                except ValueError:
                    raise errors.ValidationError(
                        'width', 'Width must be a positive integer')

                data = numpy.zeros([height, width], dtype=numpy.float32)
                if request.args.get('pixel_value') is not None:
                    try:
                        pixel_value = float(request.args['pixel_value'])
                    except ValueError:
                        raise errors.ValidationError(
                            'pixel_value', 'Pixel value must be a number')
                    else:
                        # noinspection PyPropertyAccess
                        data += pixel_value

                all_data_files.append(create_data_file(
                    adb, name, root, data, duplicates='append'))
            else:
                # Import data file from the specified provider
                import_params = request.args.to_dict()
                provider_id = import_params.pop('provider_id', None)
                duplicates = import_params.pop('duplicates', 'ignore')
                if provider_id is None:
                    # Data file upload: get data from request body
                    all_data_files += import_data_file(
                        adb, root, None, None, import_params,
                        BytesIO(request.data), import_params.get('name'),
                        duplicates)
                else:
                    # Import data from the given data provider
                    try:
                        asset_path = import_params.pop('path')
                    except KeyError:
                        raise errors.MissingFieldError('path')

                    try:
                        provider = data_providers.providers[provider_id]
                    except KeyError:
                        raise data_providers.UnknownDataProviderError(
                            id=provider_id)
                    provider_id = provider.id

                    recurse = import_params.pop('recurse', False)

                    def recursive_import(path, depth=0):
                        asset = provider.get_asset(path)
                        if asset.collection:
                            if not provider.browseable:
                                raise CannotImportFromCollectionAssetError(
                                    provider_id=provider_id, path=path)
                            if not recurse and depth:
                                return []
                            return sum(
                                [recursive_import(child_asset.path, depth + 1)
                                 for child_asset in provider.get_child_assets(
                                    asset.path)], [])
                        return import_data_file(
                            adb, root, provider_id, asset.path, asset.metadata,
                            BytesIO(provider.get_asset_data(asset.path)),
                            asset.name, duplicates)

                    if not isinstance(asset_path, list):
                        try:
                            asset_path = json.loads(asset_path)
                        except ValueError:
                            pass
                        if not isinstance(asset_path, list):
                            asset_path = [asset_path]
                    all_data_files += sum(
                        [recursive_import(p) for p in asset_path], [])

            if all_data_files:
                adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response(all_data_files, 201 if all_data_files else 200)

    if request.method == 'PUT':
        # Update data file
        name = request.args.get('name')
        if name:
            try:
                data_file.name = name
                adb.commit()
            except Exception:
                adb.rollback()
                raise

        return json_response(DataFile(data_file))

    if request.method == 'DELETE':
        # Delete data file
        try:
            adb.query(SqlaDataFile).filter(SqlaDataFile.id == id).delete()
            for filename in glob(os.path.join(root, '{}.*'.format(id))):
                try:
                    os.remove(filename)
                except Exception as e:
                    app.logger.warn(
                        'Error removing data file "%s" (ID %d) [%s]',
                        filename, id,
                        e.message if hasattr(e, 'message') and e.message
                        else ', '.join(str(arg) for arg in e.args) if e.args
                        else e)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response()


@app.route(resource_prefix + '<int:id>/header', methods=['GET', 'PUT'])
@auth_required('user')
def data_files_header(id):
    """
    Return or update data file header

    GET /data-files/[id]/header

    PUT /data-files/[id]/header?keyword=value...

    :param int id: data file ID

    :return: JSON-serialized structure
        [{"key": key, "value": value, "comment": comment}, ...]
        containing the data file header cards in the order they appear in the
        underlying FITS file header
    :rtype: flask.Response | str
    """

    if request.method == 'GET':
        hdr = get_data_file(current_user.id, id)[1]
    else:
        with pyfits.open(get_data_file_path(current_user.id, id),
                         'update') as fits:
            hdr = fits[0].header
            for name, val in request.args.items():
                hdr[name] = val

    return json_response([
        dict(key=key, value=value, comment=hdr.comments[i])
        for i, (key, value) in enumerate(hdr.items())])


@app.route(resource_prefix + '<int:id>/hist')
@auth_required('user')
def data_files_hist(id):
    """
    Return the data file histogram

    GET /data-files/[id]/hist

    The number of bins in the histogram is controlled by the HISTOGRAM_BINS
    configuration variable. It is either the fixed number of bins or a name of
    the method used to adaptively calculate the number of bins required to
    adequately represent the data; see
    `https://docs.scipy.org/doc/numpy/reference/generated/numpy.histogram.html`_

    :param int id: data file ID

    :return: JSON-serialized structure
        {"data": [value, value, ...], "min_bin": min_bin, "max_bin": max_bin}
        containing the integer-valued histogram data array and the
        floating-point left and right histogram limits set from the data
    :rtype: flask.Response
    """
    root = get_root(current_user.id)

    # noinspection PyBroadException
    try:
        # First try using the cached histogram
        with pyfits.open(
                os.path.join(root, '{}.fits.hist'.format(id)), 'readonly',
                uint=True) as hist:
            hdr = hist[0].header
            min_bin, max_bin = hdr['MINBIN'], hdr['MAXBIN']
            data = hist[0].data
    except Exception:
        # Cached histogram not found, calculate and return
        try:
            data = get_data_file(current_user.id, id)[0]
            min_bin, max_bin = float(data.min()), float(data.max())
            bins = app.config['HISTOGRAM_BINS']
            if isinstance(bins, int) and not (data % 1).any():
                if max_bin - min_bin < 0x100:
                    # 8-bit integer data; use 256 bins maximum
                    bins = min(bins, 0x100)
                elif max_bin - min_bin < 0x10000:
                    # 16-bit integer data; use 65536 bins maximum
                    bins = min(bins, 0x10000)
            if max_bin == min_bin:
                # Constant data, use unit bin size if the number of bins
                # is fixed or unit range otherwise
                if isinstance(bins, int):
                    max_bin = min_bin + bins
                else:
                    max_bin = min_bin + 1
            data = numpy.histogram(data, bins, (min_bin, max_bin))[0]

            # Cache histogram and limits
            # noinspection PyTypeChecker
            hist = pyfits.PrimaryHDU(data)
            hist.header['MINBIN'] = min_bin, 'Lower histogram boundary'
            hist.header['MAXBIN'] = max_bin, 'Upper histogram boundary'
            hist.writeto(
                os.path.join(root, '{}.fits.hist'.format(id)),
                overwrite=True)
        except errors.AfterglowError:
            raise
        except Exception:
            raise UnknownDataFileError(id=id)

    return json_response(
        dict(data=data.tolist(), min_bin=min_bin, max_bin=max_bin))


@app.route(resource_prefix + '<int:id>/pixels')
@auth_required('user')
def data_files_pixels(id):
    """
    Return image data within the given rectangle or the whole image

    GET /data-files/[id]/pixels?x=...&y=...&width=...&height=...

    By default, x and y are set to 1, width = image width - (x - 1), height =
    image height - (y - 1).

    Depending on the request headers (Accept and Accept-Encoding), the pixel
    data are returned either as an optionally gzipped binary stream or as
    a JSON list.

    [Accept: application/octet-stream]
    [Accept: */octet-stream]
    [Accept: application/*]
    [Accept: */*]
    -> (uncompressed binary)
    Content-Type: application/octet-stream

    [Accept: application/octet-stream]
    [Accept: */octet-stream]
    [Accept: application/*]
    [Accept: */*]
    Accept-Encoding: gzip
    -> (compressed binary)
    Content-Type: application/octet-stream
    Content-Encoding: gzip

    [Accept: application/json]
    [Accept: */json]
    -> (JSON)
    Content-Type: application/json

    Binary data are returned in the little-endian byte order (LSB first, Intel)
    by row, i.e. in C format, from bottom to top.

    :param int id: data file ID

    :return: depending on the Accept and Accept-Encoding HTTP headers (see
        above), either the gzipped binary data (application/octet-stream) or
        a JSON list of rows, each one being, in turn, a list of data values
        within the row
    :rtype: flask.Response
    """
    try:
        return make_data_response(get_subframe(current_user.id, id))
    except errors.AfterglowError:
        raise
    except Exception:
        raise UnknownDataFileError(id=id)


@app.route(resource_prefix + '<int:id>/fits')
@auth_required('user')
def data_files_fits(id):
    """
    Return the whole data file as a FITS file

    GET /data-files/[id]/fits

    Depending on the request headers (Accept and Accept-Encoding), the FITS
    file is returned either as a gzipped or uncompressed (default) FITS.

    [Accept-Encoding:]
    [Accept-Encoding: identity]
    -> (uncompressed FITS)
    Content-Type: application/octet-stream

    Accept-Encoding: gzip
    -> (compressed FITS)
    Content-Type: application/octet-stream
    Content-Encoding: gzip

    :param int id: data file ID

    :return: depending on the Accept and Accept-Encoding HTTP headers (see
        above), either the gzipped or uncompressed FITS file data
    :rtype: flask.Response
    """
    return make_data_response(get_data_file_data(current_user.id, id))


@app.route(resource_prefix + '<int:id>/sonification')
@auth_required('user')
def data_files_sonification(id):
    """
    Sonify the image or its part and return the waveform data

    GET /data-files/[id]/sonification?x=...&y=...&width=...&height=...
        &param=value...

    By default, x and y are set to 1, width = image width - (x - 1), height =
    image height - (y - 1). Other parameters are sent to the sonification
    procedure (see skylib.sonification.sonify_image).

    Depending on the Accept request header, the sonification data are returned
    as either WAV or MP3.

    [Accept: audio/wav]
    [Accept: audio/x-wav]
    [Accept: */wav]
    [Accept: */x-wav]
    [Accept: audio/*]
    [Accept: */*]
    -> WAV
    Content-Type: audio/x-wav

    [Accept: audio/mpeg]
    [Accept: audio/mpeg3]
    [Accept: audio/x-mpeg-3]
    [Accept: */mpeg]
    [Accept: */mpeg3]
    [Accept: */x-mpeg-3]
    -> MP3
    Content-Type: audio/x-mpeg-3

    :param int id: data file ID

    :return: depending on the Accept HTTP header (see above), either WAV file
        data or MP3 file data
    :rtype: flask.Response
    """
    try:
        pixels = get_subframe(current_user.id, id)
    except errors.AfterglowError:
        raise
    except Exception:
        raise UnknownDataFileError(id=id)

    args = request.args.to_dict()
    try:
        x0 = int(args.pop('x', 1)) - 1
    except ValueError:
        x0 = 0
    try:
        y0 = int(args.pop('y', 1)) - 1
    except ValueError:
        y0 = 0
    for arg in ('width', 'height', 'bkg', 'rms', 'bkg_scale'):
        args.pop(arg, None)

    adb = get_data_file_db(current_user.id)
    df = adb.query(SqlaDataFile).get(id)
    height, width = pixels.shape
    if width != df.width or height != df.height:
        # Sonifying a subimage; estimate background from the whole image first,
        # then supply a cutout of background and RMS to sonify_image()
        try:
            bkg_scale = float(args.pop('bkg_scale', 1/64))
        except ValueError:
            bkg_scale = 1/64
        full_img = get_data_file(current_user.id, id)[0]
        bkg, rms = estimate_background(full_img, size=bkg_scale)
        bkg = bkg[y0:y0+height, x0:x0+width]
        rms = rms[y0:y0+height, x0:x0+width]
    else:
        # When sonifying the whole image, sonify_image() will estimate
        # background automatically
        bkg = rms = None

    data = BytesIO()
    sonify_image(pixels, data, bkg=bkg, rms=rms, **args)
    data = data.getvalue()

    # Figure out how to transfer sonification to the client
    accepted_mimetypes = request.headers['Accept']
    if accepted_mimetypes:
        allow_wav = allow_mp3 = False
        for mt in accepted_mimetypes.split(','):
            mtype, subtype = mt.split(';')[0].strip().lower().split('/')
            if mtype in ('audio', '*'):
                if subtype in ('wav', 'x-wav'):
                    allow_wav = True
                elif subtype in ('mpeg', 'mpeg3', 'x-mpeg-3'):
                    allow_mp3 = True
                elif subtype == '*':
                    allow_wav = allow_mp3 = True
    else:
        # Accept header not specified, assume all types are allowed
        allow_wav = allow_mp3 = True

    # Prefer sending a gzipped wav
    if allow_wav:
        return Response(data, mimetype='audio/x-wav')

    if allow_mp3:
        # Use ffmpeg to convert wav to mp3
        temp_dir = tempfile.mkdtemp(prefix='ffmpeg-')
        try:
            wav_file = os.path.join(temp_dir, 'in.wav')
            mp3_file = os.path.join(temp_dir, 'out.mp3')
            with open(wav_file, 'wb') as f:
                f.write(data)
            subprocess.check_call(['ffmpeg', '-i', wav_file, mp3_file])
            with open(mp3_file, 'rb') as f:
                data = f.read()
        finally:
            shutil.rmtree(temp_dir)

        return Response(data, mimetype='audio/x-mpeg-3')

    # Could not send sonification in any of the formats supported by the client
    raise errors.NotAcceptedError(accepted_mimetypes=accepted_mimetypes)
