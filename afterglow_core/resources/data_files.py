"""
Afterglow Core: data-files resource implementation
"""

import sys
import os
from glob import glob
from datetime import datetime
import json
import gzip
import sqlite3
from threading import Lock
from io import BytesIO

from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Integer, String,
    create_engine, event, func)
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# noinspection PyProtectedMember
from sqlalchemy.engine import Engine
import numpy
import astropy.io.fits as pyfits
from flask import Response, request

from .. import app, errors, json_response
from ..models.data_file import DataFile
from ..errors.data_file import (
    UnknownDataFileError, CannotCreateDataFileDirError)

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

try:
    from alembic import config as alembic_config, context as alembic_context
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext
except ImportError:
    ScriptDirectory = EnvironmentContext = None
    alembic_config = alembic_context = None


__all__ = [
    'Base', 'SqlaDataFile', 'SqlaSession', 'make_data_response',
    'data_files_engine', 'data_files_engine_lock', 'create_data_file',
    'save_data_file', 'get_data_file', 'remove_data_file', 'get_data_file_data',
    'get_data_file_db', 'get_data_file_fits', 'get_data_file_path',
    'get_exp_length', 'get_gain', 'get_image_time', 'get_root', 'get_subframe',
    'import_data_file', 'get_session_id', 'convert_exif_field',
]

Base = declarative_base()


class SqlaDataFile(Base):
    __tablename__ = 'data_files'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(String)
    name = Column(String, CheckConstraint('length(name) <= 1024'))
    width = Column(Integer)
    height = Column(Integer)
    data_provider = Column(String)
    asset_path = Column(String)
    asset_metadata = Column(String)
    layer = Column(String)
    created_on = Column(DateTime, default=func.now())
    session_id = Column(
        Integer,
        ForeignKey('sessions.id', name='fk_sessions_id', ondelete='cascade'),
        nullable=True, index=True)


class SqlaSession(Base):
    __tablename__ = 'sessions'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(
        String, CheckConstraint('length(name) <= 80'), unique=True,
        nullable=False)
    data = Column(
        String, CheckConstraint('data is null or length(data) <= 1048576'),
        nullable=True, server_default='')

    data_files = relationship('SqlaDataFile', backref='session')  # type: list


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
    needed and return the database object; thread-safe

    :param int | None user_id: current user ID (None if user auth is disabled)

    :return: SQLAlchemy session object
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
                session = data_files_engine[root][1]
            except KeyError:
                # Engine does not exist, create it
                @event.listens_for(Engine, 'connect')
                def set_sqlite_pragma(dbapi_connection, _rec):
                    if isinstance(dbapi_connection, sqlite3.Connection):
                        cursor = dbapi_connection.cursor()
                        cursor.execute('PRAGMA foreign_keys=ON')
                        cursor.execute('PRAGMA journal_mode=WAL')
                        cursor.close()
                engine = create_engine(
                    'sqlite:///{}'.format(os.path.join(root, 'data_files.db')),
                    connect_args={'check_same_thread': False,
                                  'isolation_level': None},
                )

                # Create data_files table
                if alembic_config is None:
                    # Alembic not available, create table from SQLA metadata
                    Base.metadata.create_all(bind=engine)
                else:
                    # Create/upgrade table via Alembic
                    cfg = alembic_config.Config()
                    cfg.set_main_option(
                        'script_location',
                        os.path.abspath(os.path.join(
                            __file__, '..', '..', 'db_migration', 'data_files'))
                    )
                    script = ScriptDirectory.from_config(cfg)

                    # noinspection PyProtectedMember
                    with EnvironmentContext(
                                cfg, script, fn=lambda rev, _:
                                script._upgrade_revs('head', rev),
                                as_sql=False, starting_rev=None,
                                destination_rev='head', tag=None,
                            ), engine.connect() as connection:
                        alembic_context.configure(connection=connection)

                        with alembic_context.begin_transaction():
                            alembic_context.run_migrations()

                session = scoped_session(sessionmaker(bind=engine))
                data_files_engine[root] = engine, session

        session()
        return session

    except Exception as e:
        # noinspection PyUnresolvedReferences
        raise CannotCreateDataFileDirError(
            reason=e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e))


def save_data_file(root, file_id, data, hdr):
    """
    Save data file to the user's data file directory as a single (image) or
    double (image + mask) HDU FITS or a primary + table HDU FITS, depending on
    whether the input HDU contains an image or a table

    :param str root: user's data file storage root directory
    :param int file_id: data file ID
    :param array_like data: image or table data; image data can be a masked
        array
    :param astropy.io.fits.Header hdr: FITS header

    :return: None
    """
    # Initialize header
    if hdr is None:
        hdr = pyfits.Header()
    hdr['FILE_ID'] = (file_id, 'Afterglow data file ID')

    if data.dtype.fields is None:
        # Convert image data to float32
        data = data.astype(numpy.float32)
        if isinstance(data, numpy.ma.MaskedArray) and not data.mask.any():
            # Empty mask, save as normal array
            data = data.data
        if isinstance(data, numpy.ma.MaskedArray):
            # Store masked array in two HDUs
            fits = pyfits.HDUList(
                [pyfits.PrimaryHDU(data.data, hdr),
                 pyfits.ImageHDU(data.mask.astype(numpy.uint8), name='MASK')])
        else:
            # Treat normal arrays with NaN's as masked arrays
            mask = numpy.isnan(data)
            if mask.any():
                fits = pyfits.HDUList(
                    [pyfits.PrimaryHDU(data, hdr),
                     pyfits.ImageHDU(mask, name='MASK')])
            else:
                fits = pyfits.PrimaryHDU(data, hdr)
    else:
        fits = pyfits.BinTableHDU(data, hdr)

    # Save FITS to data file directory
    fits.writeto(
        os.path.join(root, '{}.fits'.format(file_id)),
        'silentfix', overwrite=True)


def create_data_file(adb, name, root, data, hdr=None, provider=None, path=None,
                     metadata=None, layer=None, duplicates='ignore',
                     session_id=None):
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
    :param int | None session_id: optional user session ID; defaults to
        anonymous session

    :return: data file instance
    :rtype: afterglow_core.models.data_file.DataFile
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
        session_id=session_id,
    )

    if duplicates in ('ignore', 'overwrite'):
        # Look for an existing data file with the same import parameters
        sqla_data_file = adb.query(SqlaDataFile).filter_by(
            data_provider=provider, asset_path=path, layer=layer,
            session_id=session_id,
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


def remove_data_file(adb, root, id):
    """
    Remove the given data file from database and delete all associated disk
    files

    :param sqlalchemy.orm.session.Session adb: SQLA database session
    :param str root: user's data file storage root directory
    :param int id: data file ID

    :return: None
    """
    adb.query(SqlaDataFile).filter(SqlaDataFile.id == id).delete()
    for filename in glob(os.path.join(root, '{}.*'.format(id))):
        try:
            os.remove(filename)
        except Exception as e:
            # noinspection PyUnresolvedReferences
            app.logger.warn(
                'Error removing data file "%s" (ID %d) [%s]',
                filename, id,
                e.message if hasattr(e, 'message') and e.message
                else ', '.join(str(arg) for arg in e.args) if e.args
                else e)


def import_data_file(adb, root, provider_id, asset_path, asset_metadata, fp,
                     name, duplicates='ignore', session_id=None):
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
    :param int | None session_id: optional user session ID; defaults to
        anonymous session

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
                    if layer:
                        # Check that the filter is unique among other HDUs
                        if any(_hdu.header.get('FILTER') == layer
                               for _hdu in fits if _hdu is not hdu):
                            layer += '.' + str(i + 1)
                    else:
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
                    asset_path, asset_metadata, layer, duplicates, session_id))

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
                asset_metadata, layer, duplicates, session_id))

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
                not isinstance(val, str) and not isinstance(val, type(u'')):
            val = val[0]

    if isinstance(val, tuple) and len(val) == 2:
        # PIL ratio
        return val[0]/val[1]

    if hasattr(val, 'num') and hasattr(val, 'den'):
        # ExifRead ratio
        if val.den:
            return float(val.num)/float(val.den)
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


def get_data_file_fits(user_id, file_id, mode='readonly'):
    """
    Return FITS file given the data file ID

    :param int | None user_id: current user ID (None if user auth is disabled)
    :param int file_id: data file ID
    :param str mode: optional FITS file open mode: "readonly" (default)
        or "update"

    :return: FITS file object
    :rtype: astropy.io.fits.HDUList
    """
    try:
        return pyfits.open(get_data_file_path(user_id, file_id), mode)
    except Exception:
        raise UnknownDataFileError(id=file_id)


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
    fits = get_data_file_fits(user_id, file_id)

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
            data = numpy.ma.MaskedArray(fits[0].data, fits[1].data.astype(bool))
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


def get_session_id(adb):
    """
    Helper function used by resource handlers to retrieve session ID from
    request arguments and check that the session (if any) exists

    :param sqlalchemy.orm.session.Session adb: SQLA database session

    :return: session ID or None if none supplied
    :rtype: int | None
    """
    session_id = request.args.get('session_id')
    if session_id is None:
        return

    session = adb.query(SqlaSession).get(session_id)
    if session is None:
        session = adb.query(SqlaSession).filter(
            SqlaSession.name == session_id).one_or_none()
    if session is None:
        raise errors.ValidationError(
            'session_id', 'Unknown session "{}"'.format(session_id),
            404)
    return session.id
