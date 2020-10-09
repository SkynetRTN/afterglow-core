"""
Afterglow Core: data-files resource implementation
"""

import sys
import os
from glob import glob
from datetime import datetime
import json
import sqlite3
import uuid
from threading import Lock
from io import BytesIO
from typing import Dict as TDict, List as TList, Optional, Tuple, Union

from sqlalchemy import (
    Boolean, CheckConstraint, Column, ForeignKey, Integer, String,
    create_engine, event)
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# noinspection PyProtectedMember
from sqlalchemy.engine import Engine
import numpy
import astropy.io.fits as pyfits

from .. import app, errors
from ..models import DataFile, Session
from ..errors.data_file import (
    UnknownDataFileError, CannotCreateDataFileDirError,
    CannotImportFromCollectionAssetError, UnknownSessionError,
    DuplicateSessionNameError, UnrecognizedDataFormatError,
    UnknownDataFileGroupError, DataFileExportError)
from ..errors.data_provider import UnknownDataProviderError
from . import data_providers
from .base import DateTime, JSONType

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
    # Data file db
    'DataFileBase', 'data_files_engine',
    'data_files_engine_lock', 'get_data_file_db',
    # Paths
    'get_root', 'get_data_file_path',
    # Metadata
    'convert_exif_field', 'get_exp_length', 'get_gain', 'get_image_time',
    # Data/metadata retrieval
    'get_data_file_bytes', 'get_data_file_data', 'get_data_file_fits',
    'get_data_file_group_bytes', 'get_subframe',
    # Data file creation
    'create_data_file', 'import_data_file', 'save_data_file',
    # API endpoint interface
    'delete_data_file', 'get_data_file', 'get_data_file_group',
    'import_data_files', 'query_data_files', 'update_data_file',
    # Sessions
    'get_session', 'query_sessions', 'create_session', 'update_session',
    'delete_session',
]


DataFileBase = declarative_base()


class DbDataFile(DataFileBase):
    __tablename__ = 'data_files'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(String)
    name = Column(String, CheckConstraint('length(name) <= 1024'))
    width = Column(Integer)
    height = Column(Integer)
    data_provider = Column(String)
    asset_path = Column(String)
    asset_metadata = Column(JSONType)
    layer = Column(String)
    created_on = Column(DateTime, default=datetime.utcnow)
    modified = Column(Boolean, default=False)
    modified_on = Column(DateTime, onupdate=datetime.utcnow)
    session_id = Column(
        Integer,
        ForeignKey('sessions.id', name='fk_sessions_id', ondelete='cascade'),
        nullable=True, index=True)
    group_id = Column(
        String, CheckConstraint('length(group_id) = 36'), nullable=False,
        index=True)
    group_order = Column(Integer, nullable=False, server_default='0')


class DbSession(DataFileBase):
    __tablename__ = 'sessions'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(
        String, CheckConstraint('length(name) <= 80'), unique=True,
        nullable=False)
    data = Column(
        String, CheckConstraint('data is null or length(data) <= 1048576'),
        nullable=True, server_default='')

    data_files: TList[DbDataFile] = relationship(
        'DbDataFile', backref='session')


def get_root(user_id: Optional[int]) -> str:
    """
    Return the absolute path to the current authenticated user's data storage
    root directory

    :param user_id: current user ID (None if user auth is disabled)

    :return: user's data storage path
    """
    root = app.config['DATA_FILE_ROOT']
    if user_id:
        root = os.path.join(root, str(user_id))
    return os.path.abspath(os.path.expanduser(root))


# SQLA database engine
data_files_engine = {}
data_files_engine_lock = Lock()


def get_data_file_db(user_id: Optional[int]):
    """
    Initialize the given user's data file storage directory and database as
    needed and return the database object; thread-safe

    :param user_id: current user ID (None if user auth is disabled)

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
                    DataFileBase.metadata.create_all(bind=engine)
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


def save_data_file(adb, root: str, file_id: int, data: numpy.ndarray, hdr,
                   modified: bool = True) \
        -> None:
    """
    Save data file to the user's data file directory as a single (image) or
    double (image + mask) HDU FITS or a primary + table HDU FITS, depending on
    whether the input HDU contains an image or a table

    :param adb: SQLA database session
    :param root: user's data file storage root directory
    :param file_id: data file ID
    :param data: image or table data; image data can be a masked array
    :param hdr: FITS header
    :param modified: if True, set the file modification flag; not set on initial
        creation
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

    # Update image dimensions and file modification timestamp
    db_data_file = adb.query(DbDataFile).get(file_id)
    if data.dtype.fields is None:
        # Image: get image dimensions from array shape
        db_data_file.height, db_data_file.width = data.shape
    else:
        # Table: width = number of columns, height = number of rows
        db_data_file.width = len(data.dtype.fields)
        db_data_file.height = len(data)
    if modified:
        db_data_file.modified = True


def create_data_file(adb, name: Optional[str], root: str, data: numpy.ndarray,
                     hdr=None, provider: str = None, path: str = None,
                     metadata: dict = None, layer: str = None,
                     duplicates: str = 'ignore',
                     session_id: Optional[int] = None,
                     group_id: Optional[str] = None,
                     group_order: Optional[int] = 0) -> DbDataFile:
    """
    Create a database entry for a new data file and save it to data file
    directory as an single (image) or double (image + mask) HDU FITS or
    a primary + table HDU FITS, depending on whether the input HDU contains
    an image or a table

    :param adb: SQLA database session
    :param name: data file name
    :param root: user's data file storage root directory
    :param data: image or table data; image data can be a masked array
    :param hdr: FITS header
    :param provider: data provider ID/name if not creating an empty data file
    :param path: path of the data provider asset the file was imported from
    :param metadata: data provider asset metadata
    :param layer: optional layer ID for multiple-layer assets
    :param duplicates: optional duplicate handling mode used if the data file
        with the same `provider`, `path`, and `layer` was already imported
        before: "ignore" (default) = don't re-import the existing data file,
        "overwrite" = re-import the file and replace the existing data file,
        "append" = always import as a new data file
    :param session_id: optional user session ID; defaults to anonymous session
    :param group_id: optional GUID of the file group; default: auto-generate
    :param group_order: 0-based order of the file in the group

    :return: data file instance
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

    if group_id is None:
        # Auto-generate group ID
        group_id = str(uuid.uuid4())

    # Create/update a database row
    sqla_fields = dict(
        type='image' if data.dtype.fields is None else 'table',
        name=name,
        width=width,
        height=height,
        data_provider=provider,
        asset_path=path,
        asset_metadata=metadata,
        layer=layer,
        session_id=session_id,
        group_id=group_id,
        group_order=group_order,
    )

    if duplicates in ('ignore', 'overwrite'):
        # Look for an existing data file with the same import parameters
        db_data_file = adb.query(DbDataFile).filter_by(
            data_provider=provider, asset_path=path, layer=layer,
            session_id=session_id,
        ).one_or_none()

        if db_data_file is not None:
            if duplicates == 'ignore':
                # Don't reimport existing data files
                return db_data_file

            # Overwrite existing data file
            for attr, val in sqla_fields.items():
                setattr(db_data_file, attr, val)
    else:
        db_data_file = None

    if db_data_file is None:
        # Add a database row and obtain its ID
        db_data_file = DbDataFile(**sqla_fields)
        adb.add(db_data_file)
        adb.flush()  # obtain the new row ID by flushing db

    save_data_file(adb, root, db_data_file.id, data, hdr, modified=False)

    return db_data_file


def import_data_file(adb, root: str, provider_id: Optional[str],
                     asset_path: Optional[str], asset_metadata: dict, fp,
                     name: Optional[str], duplicates: str = 'ignore',
                     session_id: Optional[int] = None) -> TList[DbDataFile]:
    """
    Create data file(s) from a (possibly multi-layer) non-collection data
    provider asset or from an uploaded file

    :param adb: SQLA database session
    :param root: user's data file storage root directory
    :param provider_id: data provider ID/name
    :param asset_path: data provider asset path
    :param asset_metadata: data provider asset metadata
    :param fp: file-like object containing the asset data, should be opened for
        reading
    :param name: data file name
    :param duplicates: optional duplicate handling mode used if the data file
        with the same `provider`, `path`, and `layer` was already imported
        before: "ignore" (default) = don't re-import the existing data file,
        "overwrite" = re-import the file and replace the existing data file,
        "append" = always import as a new data file
    :param session_id: optional user session ID; defaults to anonymous session

    :return: list of DbDataFile instances created/updated
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

            # Generate group ID for all HDUs
            group_id = str(uuid.uuid4())

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
                    # DbDataFile.name (e.g. filter name)
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

                asset_metadata['type'] = 'FITS'

                all_data_files.append(create_data_file(
                    adb, fullname, root, hdu.data, hdu.header, provider_id,
                    asset_path, asset_metadata, layer, duplicates, session_id,
                    group_id=group_id, group_order=i))

    except errors.AfterglowError:
        raise
    except Exception:
        # Non-FITS file; try importing all color planes with Pillow and rawpy
        exif = None
        channels = []

        if PILImage is not None:
            # noinspection PyBroadException
            try:
                fp.seek(0)
                with PILImage.open(fp) as im:
                    asset_metadata['type'] = im.format
                    asset_metadata['image_mode'] = im.mode
                    width, height = im.size
                    band_names = im.getbands()
                    asset_metadata['layers'] = len(band_names)
                    if len(band_names) > 1:
                        bands = im.split()
                    else:
                        bands = (im,)
                    channels = {
                        (band_name, numpy.fromstring(
                            band.tobytes(), numpy.uint8).reshape(
                            [height, width]))
                        for band_name, band in zip(band_names, bands)}
                    if exifread is None:
                        exif = {
                            ExifTags.TAGS[key]: convert_exif_field(val)
                            for key, val in im.getexif().items()
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
                try:
                    asset_metadata['type'] = str(im.raw_type)
                    asset_metadata['image_mode'] = im.color_desc.decode('ascii')
                    asset_metadata['layers'] = im.num_colors
                    r, g, b = numpy.rollaxis(im.postprocess(output_bps=16), 2)
                finally:
                    im.close()
                channels = [('R', r), ('G', g), ('B', b)]
            except Exception:
                pass

        if not channels:
            raise UnrecognizedDataFormatError()

        if exifread is not None:
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
                    t = datetime.strptime(str(t), '%Y:%m:%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        t = datetime.strptime(str(t), '%Y:%m:%d %H:%M:%S')
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

        group_id = str(uuid.uuid4())
        for i, (channel, data) in enumerate(channels):
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
                asset_metadata, layer, duplicates, session_id,
                group_id=group_id, group_order=i))

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


def get_subframe(user_id: Optional[int], file_id: int,
                 x0: Optional[int] = None, y0: Optional[int] = None,
                 w: Optional[int] = None, h: Optional[int] = None) \
        -> numpy.ndarray:
    """
    Return pixel data for the given image data file ID within a rectangle
    defined by the optional request parameters "x", "y", "width", and "height";
    XY are in the FITS system with (1,1) at the bottom left corner of the image

    :param user_id: current user ID (None if user auth is disabled)
    :param file_id: data file ID
    :param x0: optional subframe origin X coordinate (1-based)
    :param y0: optional subframe origin Y coordinate (1-based)
    :param w: optional subframe width
    :param h: optional subframe height

    :return: NumPy float32 array containing image data within the specified
        region
    """
    data = get_data_file_data(user_id, file_id)[0]
    is_image = data.dtype.fields is None
    if is_image:
        height, width = data.shape
    else:
        # FITS table
        width = len(data.dtype.fields)
        height = len(data)

    if x0 is None:
        x0 = 1
    try:
        x0 = int(x0) - 1
        if x0 < 0 or x0 >= width:
            raise errors.ValidationError(
                'x', 'X must be positive and not greater than image width', 422)
    except ValueError:
        raise errors.ValidationError('x', 'X must be a positive integer')

    if y0 is None:
        y0 = 1
    try:
        y0 = int(y0) - 1
        if y0 < 0 or y0 >= height:
            raise errors.ValidationError(
                'y', 'Y must be positive and not greater than image height',
                422)
    except ValueError:
        raise errors.ValidationError('y', 'Y must be a positive integer')

    if not w:
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

    if not h:
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


def get_data_file_path(user_id: Optional[int], file_id: int) -> str:
    """
    Return data file path on disk

    :param int | None user_id: current user ID (None if user auth is disabled)
    :param int file_id: data file ID

    :return: path to data file
    """
    return os.path.join(get_root(user_id), '{}.fits'.format(file_id))


def get_data_file_fits(user_id: Optional[int], file_id: int,
                       mode: str = 'readonly') -> pyfits.HDUList:
    """
    Return FITS file given the data file ID

    :param user_id: current user ID (None if user auth is disabled)
    :param file_id: data file ID
    :param mode: optional FITS file open mode: "readonly" (default) or "update"

    :return: FITS file object
    """
    try:
        return pyfits.open(get_data_file_path(user_id, file_id), mode)
    except Exception:
        raise UnknownDataFileError(id=file_id)


def get_data_file_data(user_id: Optional[int], file_id: int) \
        -> Tuple[numpy.ndarray, pyfits.Header]:
    """
    Return FITS file data and header for a data file with the given ID; handles
    masked images

    :param user_id: current user ID (None if user auth is disabled)
    :param file_id: data file ID

    :return: tuple (data, hdr); if the underlying FITS file contains a mask in
        an extra image HDU, it is converted into a :class:`numpy.ma.MaskedArray`
        instance
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


def get_data_file_uint8(user_id: Optional[int], file_id: int) -> numpy.ndarray:
    """
    Return image file data array scaled to 8-bit unsigned integer format
    suitable for exporting to PNG, JPEG, etc.

    :param user_id: current user ID (None if user auth is disabled)
    :param file_id: data file ID

    :return: uint8 image data; masked values are set to 0
    """
    data = get_data_file_data(user_id, file_id)[0]
    if data.dtype.fields is not None:
        raise DataFileExportError(reason='Cannot export non-image data files')
    mn, mx = data.min(), data.max()
    if mn >= mx:
        return numpy.zeros(data.shape, numpy.uint8)
    data = ((data - mn)/(mx - mn)*255 + 0.5).astype(numpy.uint8)
    if isinstance(data, numpy.ma.MaskedArray) and data.mask is not None:
        data = numpy.where(data.mask, 0, data.data)
    return data


def get_data_file_bytes(user_id: Optional[int], file_id: int,
                        fmt: str = 'FITS') -> bytes:
    """
    Return FITS file data for data file with the given ID

    :param user_id: current user ID (None if user auth is disabled)
    :param file_id: data file ID
    :param fmt: image export format: FITS (default) or any supported by Pillow

    :return: data file bytes
    """
    if fmt == 'FITS':
        try:
            with open(get_data_file_path(user_id, file_id), 'rb') as f:
                return f.read()
        except Exception:
            raise UnknownDataFileError(id=file_id)

    if PILImage is None:
        raise DataFileExportError(reason='Server does not support image export')

    # Export image via Pillow using the specified mode
    data = get_data_file_uint8(user_id, file_id)
    buf = BytesIO()
    try:
        PILImage.fromarray(data).save(buf, format=fmt)
    except Exception as e:
        raise DataFileExportError(reason=str(e))
    return buf.getvalue()


def get_data_file_group_bytes(user_id: Optional[int], group_id: str,
                              fmt: str = 'FITS',
                              mode: Optional[str] = None) -> bytes:
    """
    Return data combined from a data file group in the original format, suitable
    for exporting to data provider

    :param user_id: current user ID (None if user auth is disabled)
    :param group_id: data file group ID
    :param fmt: image export format: FITS (default) or any supported by Pillow
    :param mode: for non-FITS formats, Pillow image mode
        (https://pillow.readthedocs.io/en/stable/handbook/concepts.html)

    :return: data file bytes
    """
    data_files = [(df.id, df.type)
                  for df in get_data_file_db(user_id).query(DbDataFile)
                  .filter(DbDataFile.group_id == group_id)
                  .order_by(DbDataFile.group_order)]
    if not data_files:
        raise UnknownDataFileGroupError(id=group_id)

    buf = BytesIO()
    if fmt == 'FITS':
        # Assemble individual single-HDU data files into a single multi-HDU FITS
        fits = pyfits.HDUList()
        for file_id, hdu_type in data_files:
            with open(get_data_file_path(user_id, file_id), 'rb') as f:
                data = f.read()
            if hdu_type == 'image':
                fits.append(pyfits.ImageHDU.fromstring(data))
            else:
                fits.append(pyfits.BinTableHDU.fromstring(data))
        fits.writeto(buf, output_verify='silentfix')
    elif PILImage is None:
        raise DataFileExportError(reason='Server does not support image export')
    else:
        # Export image via Pillow using the specified mode
        if len(data_files) > 1:
            if not mode:
                raise errors.MissingFieldError(field='mode')
            if mode not in PILImage.MODES:
                raise DataFileExportError(
                    reason='Unsupported image export mode "{}"'.format(mode))
        if any(hdu_type != 'image' for _, hdu_type in data_files):
            raise DataFileExportError(
                reason='Cannot export non-image data files')
        try:
            if len(data_files) > 1:
                im = PILImage.merge(
                    mode,
                    [PILImage.fromarray(get_data_file_uint8(user_id, file_id))
                     for file_id, _ in data_files])
            else:
                im = PILImage.fromarray(get_data_file_uint8(
                    user_id, data_files[0][0]))
            im.save(buf, format=fmt)
        except errors.AfterglowError:
            raise
        except Exception as e:
            raise DataFileExportError(reason=str(e))
    return buf.getvalue()


def get_image_time(hdr: pyfits.Header) -> Optional[datetime]:
    """
    Get exposure start time from FITS header

    :param hdr: FITS file header

    :return: exposure start time; None if unknown
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
        return datetime.strptime(dateobs, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        try:
            return datetime.strptime(dateobs, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            return None


def get_exp_length(hdr: pyfits.Header) -> float:
    """
    Get exposure length from FITS header

    :param hdr: FITS file header

    :return: exposure length in seconds; None if unknown
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


def get_gain(hdr: pyfits.Header) -> float:
    """
    Get effective gain from FITS header

    :param hdr: FITS file header

    :return: effective gain in e-/ADU; None if unknown
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


def get_data_file(user_id: Optional[int], file_id: int) -> DataFile:
    """
    Return data file object for the given ID

    :param user_id: current user ID (None if user auth is disabled)
    :param file_id: data file ID

    :return: data file object
    """
    adb = get_data_file_db(user_id)

    try:
        db_data_file = adb.query(DbDataFile).get(int(file_id))
    except ValueError:
        db_data_file = None
    if db_data_file is None:
        raise UnknownDataFileError(id=file_id)

    # Convert to data model object
    return DataFile(db_data_file)


def get_data_file_group(user_id: Optional[int], group_id: str) \
        -> TList[DataFile]:
    """
    Return data file objects belonging to the given group

    :param user_id: current user ID (None if user auth is disabled)
    :param group_id: data file group ID

    :return: data file objects sorted by group_order
    """
    adb = get_data_file_db(user_id)

    return [DataFile(db_data_file)
            for db_data_file in adb.query(DbDataFile)
            .filter(DbDataFile.group_id == group_id)
            .order_by(DbDataFile.group_order)]


def query_data_files(user_id: Optional[int], session_id: Optional[int]) \
        -> TList[DataFile]:
    """
    Return data file objects matching the given criteria

    :param user_id: current user ID (None if user auth is disabled)
    :param session_id: only return data files belonging to the given session

    :return: list of data file objects
    """
    adb = get_data_file_db(user_id)

    if session_id is not None:
        session = adb.query(Session).get(session_id)
        if session is None:
            session = adb.query(Session).filter(
                Session.name == session_id).one_or_none()
        if session is None:
            raise errors.ValidationError(
                'session_id', 'Unknown session "{}"'.format(session_id),
                404)
        session_id = session.id

    return [DataFile(db_data_file)
            for db_data_file in adb.query(DbDataFile).filter(
            DbDataFile.session_id == session_id)]


def import_data_files(user_id: Optional[int], session_id: Optional[int] = None,
                      provider_id: Union[int, str] = None,
                      path: Optional[Union[TList[str], str]] = None,
                      name: Optional[str] = None,
                      duplicates: str = 'ignore',
                      recurse: bool = False,
                      width: Optional[int] = None, height: Optional[int] = None,
                      pixel_value: float = 0,
                      files: Optional[TDict[str, bytes]] = None) \
        -> TList[DataFile]:
    """
    Create, import, or upload data files defined by request parameters:
        `provider_id` = None:
            `files` = None: create empty data file defined by `width`, `height`,
                and `pixel_value`
            `files` != None: upload data files specified by `files`
        `provider_id` != None: import data files from `path` in the given
            provider

    :param user_id: current user ID (None if user auth is disabled)
    :param session_id: import data files to the given session
    :param provider_id: optional data provider ID to import from
    :param path: asset path(s) within the data provider, JSON or Python list;
        used if `provider_id` != None
    :param name: data file name; if omitted, obtained from asset metadata
        on import, filename on upload, or automatically generated otherwise
    :param width: new image width; ignored unless `provider_id` or `files`
        are provided
    :param height: new image height; ignored unless `provider_id` or `files`
        are provided
    :param pixel_value: new image counts; ignored unless `provider_id` or
        `files` are provided
    :param duplicates: optional duplicate handling mode used if the data file
        with the same provider, path, and layer was already imported before:
        "ignore" (default) = don't re-import the existing data file,
        "overwrite" = re-import the file and replace the existing data file,
        "append" = always import as a new data file;
        ignored if `provider_id` = None
    :param recurse: recursively import collection assets; ignored unless
        `provider_id` != None
    :param files: files to upload {name: data, ...}

    :return: list of imported data files
    """
    adb = get_data_file_db(user_id)
    root = get_root(user_id)

    all_data_files = []

    try:
        if provider_id is None and not files:
            # Create an empty image data file
            if width is None:
                raise errors.MissingFieldError('width')
            try:
                width = int(width)
                if width < 1:
                    raise errors.ValidationError(
                        'width', 'Width must be positive', 422)
            except ValueError:
                raise errors.ValidationError(
                    'width', 'Width must be a positive integer')
            if height is None:
                raise errors.MissingFieldError('height')
            try:
                height = int(height)
                if height < 1:
                    raise errors.ValidationError(
                        'height', 'Height must be positive', 422)
            except ValueError:
                raise errors.ValidationError(
                    'width', 'Width must be a positive integer')

            data = numpy.zeros([height, width], dtype=numpy.float32)
            if pixel_value is not None:
                try:
                    pixel_value = float(pixel_value)
                except ValueError:
                    raise errors.ValidationError(
                        'pixel_value', 'Pixel value must be a number')
                else:
                    # noinspection PyPropertyAccess
                    data += pixel_value

            all_data_files.append(create_data_file(
                adb, name, root, data, duplicates='append',
                session_id=session_id))
        elif provider_id is None:
            # Data file upload: get from multipart/form-data; use filename
            # for the 2nd and subsequent files or if the "name" parameter
            # is not provided
            for i, (filename, file) in enumerate(files.items()):
                all_data_files += import_data_file(
                    adb, root, None, None, {}, BytesIO(file.read()),
                    filename if i else name or filename,
                    duplicates='append', session_id=session_id)
        else:
            # Import data file
            if path is None:
                raise errors.MissingFieldError('path')

            try:
                provider = data_providers.providers[provider_id]
            except KeyError:
                raise UnknownDataProviderError(id=provider_id)
            provider_id = provider.id

            def recursive_import(_path, depth=0):
                asset = provider.get_asset(_path)
                if asset.collection:
                    if not provider.browseable:
                        raise CannotImportFromCollectionAssetError(
                            provider_id=provider_id, path=_path)
                    if not recurse and depth:
                        return []
                    return sum(
                        [recursive_import(child_asset.path, depth + 1)
                         for child_asset in provider.get_child_assets(
                            asset.path)], [])
                return import_data_file(
                    adb, root, provider_id, asset.path, asset.metadata,
                    BytesIO(provider.get_asset_data(asset.path)),
                    asset.name, duplicates, session_id=session_id)

            if not isinstance(path, list):
                try:
                    path = json.loads(path)
                except ValueError:
                    pass
                if not isinstance(path, list):
                    path = [path]
            all_data_files += sum([recursive_import(p) for p in path], [])

        if all_data_files:
            adb.commit()
    except Exception:
        adb.rollback()
        raise

    return [DataFile(f) for f in all_data_files]


def update_data_file(user_id: Optional[int], data_file_id: int,
                     data_file: DataFile, force: bool = False) -> DataFile:
    """
    Update the existing data file parameters

    :param user_id: current user ID (None if user auth is disabled)
    :param data_file_id: data file ID to update
    :param data_file: data_file object containing updated parameters
    :param force: if set, flag the data file as modified even if no fields were
        changed

    :return: updated field cal object
    """
    adb = get_data_file_db(user_id)

    db_data_file = adb.query(DbDataFile).get(data_file_id)
    if db_data_file is None:
        raise UnknownDataFileError(id=data_file_id)

    modified = force
    for key, val in data_file.to_dict().items():
        if key not in ('name', 'session_id', 'group_id', 'group_order'):
            continue
        if val != getattr(db_data_file, key):
            setattr(db_data_file, key, val)
            modified = True
    if modified:
        try:
            db_data_file.modified = True
            adb.flush()
            data_file = DataFile(db_data_file)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

    return data_file


def delete_data_file(user_id: Optional[int], id: int) -> None:
    """
    Remove the given data file from database and delete all associated disk
    files

    :param user_id: current user ID (None if user auth is disabled)
    :param id: data file ID
    """
    adb = get_data_file_db(user_id)
    root = get_root(user_id)

    db_data_file = adb.query(DbDataFile).get(id)
    if db_data_file is None:
        raise UnknownDataFileError(id=id)
    try:
        adb.delete(db_data_file)
        adb.commit()
    except Exception:
        adb.rollback()
        raise

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


def get_session(user_id: Optional[int], session_id: Union[int, str]) -> Session:
    """
    Return session object with the given ID or name

    :param user_id: current user ID (None if user auth is disabled)
    :param session_id: session ID

    :return: session object
    """
    adb = get_data_file_db(user_id)

    db_session = adb.query(DbSession).get(session_id)
    if db_session is None:
        db_session = adb.query(DbSession).filter(
            DbSession.name == session_id).one_or_none()
    if db_session is None:
        raise UnknownSessionError(id=session_id)

    # Convert to data model object
    return Session(db_session)


def query_sessions(user_id: Optional[int]) -> TList[Session]:
    """
    Return all user's sessions

    :param user_id: current user ID (None if user auth is disabled)

    :return: list of session objects
    """
    adb = get_data_file_db(user_id)
    return [Session(db_session) for db_session in adb.query(DbSession)]


def create_session(user_id: Optional[int], session: Session) -> Session:
    """
    Create a new session with the given parameters

    :param user_id: current user ID (None if user auth is disabled)
    :param session: session object containing all relevant parameters

    :return: new session object
    """
    adb = get_data_file_db(user_id)

    if adb.query(DbSession).filter(DbSession.name == session.name).count():
        raise DuplicateSessionNameError(name=session.name)

    # Ignore session ID if provided
    kw = session.to_dict()
    try:
        del kw['id']
    except KeyError:
        pass

    if not kw.get('name'):
        raise errors.MissingFieldError('name')

    # Create new db session object
    try:
        db_session = DbSession(**kw)
        adb.add(db_session)
        adb.flush()
        session = Session(db_session)
        adb.commit()
    except Exception:
        adb.rollback()
        raise

    return session


def update_session(user_id: Optional[int], session_id: int,
                   session: Session) -> Session:
    """
    Update the existing session

    :param user_id: current user ID (None if user auth is disabled)
    :param session_id: session ID to update
    :param session: session object containing updated parameters

    :return: updated session object
    """
    adb = get_data_file_db(user_id)

    db_session = adb.query(DbSession).get(session_id)
    if db_session is None:
        raise UnknownSessionError(id=session_id)

    for key, val in session.to_dict().items():
        if key == 'id':
            # Don't allow changing session ID
            continue
        if key == 'name' and val != db_session.name and adb.query(
                DbSession).filter(DbSession.name == val).count():
            raise DuplicateSessionNameError(name=val)
        setattr(db_session, key, val)
    try:
        session = Session(db_session)
        adb.commit()
    except Exception:
        adb.rollback()
        raise

    return session


def delete_session(user_id: Optional[int], session_id: int) -> None:
    """
    Delete session with the given ID

    :param user_id: current user ID (None if user auth is disabled)
    :param session_id: session ID to delete
    """
    adb = get_data_file_db(user_id)

    db_session = adb.query(DbSession).get(session_id)
    if db_session is None:
        raise UnknownSessionError(id=session_id)

    try:
        for file_id in [data_file.id for data_file in db_session.data_files]:
            delete_data_file(user_id, file_id)

        adb.delete(db_session)
        adb.commit()
    except Exception:
        adb.rollback()
        raise
