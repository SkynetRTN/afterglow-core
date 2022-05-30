"""
Afterglow Core: data-files resource implementation
"""

import sys
import os
import re
import shutil
from glob import glob
from datetime import datetime
import json
import sqlite3
from threading import Lock
from io import BytesIO
from typing import Dict as TDict, List as TList, Optional, Tuple, Union
import warnings
import traceback
from contextlib import contextmanager

from sqlalchemy import (
    Boolean, CheckConstraint, Column, ForeignKey, Integer, String,
    create_engine, event)
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# noinspection PyProtectedMember
from sqlalchemy.engine import Engine
from alembic import config as alembic_config, context as alembic_context
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
import numpy
import astropy.io.fits as pyfits
from astropy.wcs import FITSFixedWarning
from astropy.io.fits.verify import VerifyWarning
from portalocker import Lock as FileLock  # , RedisLock
import redis.exceptions

from .. import app, errors
from ..models import DataFile, Session
from ..errors.data_file import *
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


__all__ = [
    # Data file db
    'DataFileBase', 'data_file_engine', 'data_file_thread_lock',
    'get_data_file_db',
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
    'update_data_file_asset', 'update_data_file_group_asset',
    # Sessions
    'get_session', 'query_sessions', 'create_session', 'update_session',
    'delete_session',
]


warnings.filterwarnings('ignore', category=FITSFixedWarning)
warnings.filterwarnings('ignore', category=VerifyWarning)

DataFileBase = declarative_base()


class DbDataFile(DataFileBase):
    __tablename__ = 'data_files'
    __table_args__ = dict(sqlite_autoincrement=True)
    __mapper_args__ = dict(confirm_deleted_rows=False)

    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(String)
    name = Column(String, CheckConstraint('length(name) <= 1024'))
    width = Column(Integer)
    height = Column(Integer)
    data_provider = Column(String)
    asset_path = Column(String)
    asset_type = Column(String, server_default='FITS')
    asset_metadata = Column(JSONType)
    layer = Column(String)
    created_on = Column(DateTime, default=datetime.utcnow)
    modified = Column(Boolean, default=False)
    modified_on = Column(DateTime, onupdate=datetime.utcnow)
    session_id = Column(
        Integer,
        ForeignKey('sessions.id', name='fk_sessions_id', ondelete='cascade'),
        nullable=True, index=True)
    group_name = Column(String, nullable=False, index=True)
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
data_file_engine = {}
data_file_thread_lock = Lock()
data_file_process_lock = {}


def create_data_file_engine(root: str) -> Engine:
    """
    Return a new database engine associated with the user's data files

    :param root: user-specific data file root dir

    :return: SQLAlchemy engine object
    """
    db_path = 'sqlite:///{}'.format(os.path.join(root, 'data_files.db'))
    engine = create_engine(
        db_path,
        connect_args={'check_same_thread': False,
                      'isolation_level': None},
    )

    @event.listens_for(engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.close()

    return engine


@contextmanager
def get_data_file_db(user_id: Optional[int]):
    """
    Initialize the given user's data file storage directory and database as
    needed and return the database object; thread-safe

    :param user_id: current user ID (None if user auth is disabled)

    :return: SQLAlchemy session object
    """
    try:
        root = get_root(user_id)
        pid = os.getpid()

        # Prevent race condition occurring when the user's data file dir and db
        # are initialized by multiple web server processes and threads
        with data_file_thread_lock:  # thread locking within the same process
            # Obtain inter-process lock
            try:
                proc_lock = data_file_process_lock[user_id, pid]
            except KeyError:
                try:
                    # # Try the more robust redis version first
                    # proc_lock = RedisLock(
                    #     'afterglow_data_files_{}'.format(user_id),
                    #     timeout=30)
                    # with proc_lock:
                    #     pass
                    # Temporarily disable redis locks as they cause deadlocks
                    # in the current version of portalocker
                    # TODO: Reenable redis locks when upstream issue fixed
                    raise redis.exceptions.ConnectionError()
                except redis.exceptions.ConnectionError:
                    # Redis server not running, use file-based locking
                    lock_path = os.path.split(root)[0]
                    if os.path.isfile(lock_path):
                        os.remove(lock_path)
                    if not os.path.isdir(lock_path):
                        os.makedirs(lock_path)
                    proc_lock = FileLock(os.path.join(
                        lock_path, '.{}.lock'.format(user_id or '')),
                        timeout=30)
                data_file_process_lock[user_id, pid] = proc_lock

            # Prevent concurrent db initialization by multiple processes,
            # including those not initiated via multiprocessing, e.g. WSGI
            session = None
            with proc_lock as _lock:
                try:
                    # Make sure the user's data directory exists
                    if os.path.isfile(root):
                        os.remove(root)
                    if not os.path.isdir(root):
                        os.makedirs(root)

                    # Get engine from cache
                    session = data_file_engine[user_id, pid][1]
                    session()
                    yield session
                except KeyError:
                    # Engine does not exist in the current process, create it
                    engine = create_data_file_engine(root)

                    # Create/upgrade data file db via Alembic
                    cfg = alembic_config.Config()
                    cfg.set_main_option(
                        'script_location',
                        os.path.abspath(os.path.join(
                            __file__, '..', '..', 'db_migration',
                            'data_files'))
                    )
                    script = ScriptDirectory.from_config(cfg)

                    # noinspection PyBroadException
                    try:
                        # noinspection PyProtectedMember
                        with EnvironmentContext(
                                    cfg, script,
                                    fn=lambda rev, _:
                                    script._upgrade_revs('head', rev),
                                    as_sql=False, starting_rev=None,
                                    destination_rev='head', tag=None,
                                ), engine.connect() as connection:
                            alembic_context.configure(connection=connection)

                            with alembic_context.begin_transaction():
                                alembic_context.run_migrations()
                    except Exception:
                        # Data file db migration failed due to an incompatible
                        # migration, wipe the user's data file dir and recreate
                        # from scratch
                        print(f'Error running migration for user {user_id}')
                        traceback.print_exc()
                        engine.dispose()
                        shutil.rmtree(root)
                        os.mkdir(root)
                        engine = create_data_file_engine(root)
                        # noinspection PyProtectedMember
                        with EnvironmentContext(
                                cfg, script,
                                fn=lambda rev, _:
                                script._upgrade_revs('head', rev),
                                as_sql=False, starting_rev=None,
                                destination_rev='head', tag=None,
                        ), engine.connect() as connection:
                            alembic_context.configure(connection=connection)

                            with alembic_context.begin_transaction():
                                alembic_context.run_migrations()

                    session = scoped_session(sessionmaker(bind=engine))
                    data_file_engine[user_id, pid] = engine, session

                    # Instantiate scoped session in the current thread
                    session()

                    # Return session registry instead of session
                    yield session
                finally:
                    if session is not None:
                        session.remove()

                    if isinstance(proc_lock, FileLock):
                        # noinspection PyBroadException
                        try:
                            # Some networked filesystems require this for file
                            # locks
                            _lock.flush()
                            os.fsync(_lock.fileno())
                        except Exception:
                            pass

    except Exception as e:
        traceback.print_exc()
        raise CannotCreateDataFileDirError(
            reason=e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e))


def save_data_file(adb, root: str, file_id: int,
                   data: Union[numpy.ndarray, numpy.ma.MaskedArray], hdr,
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
    :param modified: if True, set the file modification flag; not set
        on initial creation
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
            mask = numpy.isnan(data).astype(numpy.uint8)
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
        'silentfix+ignore', overwrite=True)

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


def append_suffix(name: str, suffix: str):
    """
    Append a suffix (e.g. numeric or layer name) to a file-like name; preserve
    the original non-numeric file extension (e.g. .fits); return the unmodified
    name if it already contains this suffix

    :param name: data file name, group name, etc.
    :param suffix: suffix to append, including separator

    :return: `name` with `suffix` appended in the appropriate place
    """
    if name.endswith(suffix):
        return name

    try:
        base, ext = name.rsplit('.', 1)
        if ext:
            # noinspection PyBroadException
            try:
                int(ext)
            except Exception:
                ext = '.' + ext
            else:
                # Numeric suffix; treat as no suffix
                raise ValueError('Numeric suffix')
    except ValueError:
        base, ext = name, None
    if base.endswith(suffix):
        return name

    name = base + suffix
    if ext:
        name += ext
    return name


def create_data_file(adb, name: Optional[str], root: str, data: numpy.ndarray,
                     hdr=None, provider: Optional[str] = None,
                     path: Optional[str] = None,
                     file_type: Optional[str] = None,
                     metadata: Optional[dict] = None,
                     layer: Optional[str] = None, duplicates: str = 'ignore',
                     session_id: Optional[int] = None,
                     group_name: Optional[str] = None,
                     group_order: Optional[int] = 0,
                     allow_duplicate_file_name: bool = True,
                     allow_duplicate_group_name: bool = False) -> DbDataFile:
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
    :param file_type: original file type ("FITS", "JPEG", etc.)
    :param metadata: data provider asset metadata
    :param layer: optional layer ID for multiple-layer assets
    :param duplicates: optional duplicate handling mode used if the data file
        with the same `provider`, `path`, and `layer` was already imported
        before: "ignore" (default) = don't re-import the existing data file,
        "overwrite" = re-import the file and replace the existing data file,
        "append" = always import as a new data file
    :param session_id: optional user session ID; defaults to anonymous session
    :param group_name: optional name of the file group; default: data file name
    :param group_order: 0-based order of the file in the group
    :param allow_duplicate_file_name: don't throw an error if `name` is set,
        and one of the existing data files has the same name
    :param allow_duplicate_group_name: don't throw an error if the specified
        group name already exists; useful when importing several files
        belonging to the same group

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

        # Make sure that the auto-generated file name is unique within
        # the session
        name_cand, i = name, 1
        while adb.query(DbDataFile).filter_by(
                session_id=session_id,
                name='file_{}.fits'.format(name_cand)).count():
            name_cand = '{}_{:03d}'.format(name, i)
            i += 1
        name = 'file_{}.fits'.format(name_cand)
    elif not allow_duplicate_file_name:
        existing_file = adb.query(DbDataFile).filter_by(
            session_id=session_id, name=name).first()
        if existing_file is not None:
            raise DuplicateDataFileNameError(
                name=name, file_id=existing_file.id)

    if group_name is None or not allow_duplicate_group_name:
        if group_name is None:
            # By default, set group name equal to data file name
            group_name = name
        # Make sure that group name is unique within the session
        name_cand, i = group_name, 1
        while adb.query(DbDataFile).filter_by(
                session_id=session_id, group_name=name_cand).count():
            name_cand = append_suffix(group_name, '_{:03d}'.format(i))
            i += 1
        group_name = name_cand
    # elif not allow_duplicate_group_name and adb.query(DbDataFile).filter_by(
    #         session_id=session_id, group_name=group_name).count():
    #     # Cannot create a new data file with an explicitly set group name
    #     # matching an existing group name
    #     raise DuplicateDataFileGroupNameError(group_name=group_name)

    # Create/update a database row
    sqla_fields = dict(
        type='image' if data.dtype.fields is None else 'table',
        name=name,
        width=width,
        height=height,
        data_provider=provider,
        asset_path=path,
        asset_type=file_type or 'FITS',
        asset_metadata=metadata,
        layer=layer,
        session_id=session_id,
        group_name=group_name,
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

    try:
        if db_data_file is None:
            # Add a database row and obtain its ID
            db_data_file = DbDataFile(**sqla_fields)
            adb.add(db_data_file)
            adb.flush()  # obtain the new row ID by flushing db

        save_data_file(adb, root, db_data_file.id, data, hdr, modified=False)
    except Exception:
        adb.rollback()
        raise

    return db_data_file


def import_data_file(adb, root: str, provider_id: Optional[Union[int, str]],
                     asset_path: Optional[str], asset_metadata: dict, fp,
                     name: str, duplicates: str = 'ignore',
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
    :param name: data file name or group name if multi-layer asset
    :param duplicates: optional duplicate handling mode used if the data file
        with the same `provider`, `path`, and `layer` was already imported
        before: "ignore" (default) = don't re-import the existing data file,
        "overwrite" = re-import the file and replace the existing data file,
        "append" = always import as a new data file
    :param session_id: optional user session ID; defaults to anonymous session

    :return: list of DbDataFile instances created/updated
    """
    all_data_files = []
    group_name = name

    # A FITS file?
    # noinspection PyBroadException
    try:
        fp.seek(0)
        with pyfits.open(fp, 'readonly', memmap=False,
                         ignore_missing_end=True) as fits:
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
            layers = []
            for i, hdu in enumerate(fits):
                hdr = hdu.header
                if isinstance(hdu, pyfits.ImageHDU.__base__):
                    # Image HDU; eliminate redundant extra dimensions if any,
                    # skip non-2D images
                    imshape = hdu.shape
                    if len(imshape) < 2 or len(imshape) > 2 and \
                            len([d for d in imshape if d != 1]) != 2 or \
                            any(not d for d in imshape):
                        continue
                    if len(imshape) > 2:
                        # Remove the possible WCS keywords for degenerate
                        # (NAXISn = 1) axes
                        axis1, axis2 = [i + 1
                                        for i, n in enumerate(imshape[::-1])
                                        if n != 1]
                        for kw in list(hdr.keys()):
                            for pattern in (
                                    r'(CTYPE)([1-9])()', r'(CRPIX)([1-9])()',
                                    r'(CRVAL)([1-9])()', r'(CUNIT)([1-9])()',
                                    r'(CDELT)([1-9])()', r'(CROTA)([1-9])()',
                                    r'(CD)([1-9])(_[1-9])',
                                    r'(CD[1-9]_)([1-9])()',
                                    r'(PC)([1-9])(_[1-9])',
                                    r'(PC[1-9]_)([1-9])()',
                            ):
                                m = re.match(pattern + '$', kw)
                                if not m:
                                    continue
                                axis = int(m[2])
                                if axis in (axis1, axis2):
                                    if axis not in (1, 2):
                                        if axis == axis1:
                                            new_axis = 1
                                        else:
                                            new_axis = 2
                                        new_kw = m.re.sub(
                                            r'\g<1>{}\g<3>'.format(new_axis),
                                            kw)
                                        hdr[new_kw] = hdr[kw]
                                        try:
                                            hdr.comments[new_kw] = \
                                                hdr.comments[kw]
                                        except KeyError:
                                            pass
                                        del hdr[kw]
                                else:
                                    del hdr[kw]

                        # Eliminate degenerate axes
                        imshape = tuple([d for d in imshape if d != 1])
                        hdr['NAXIS'] = 2
                        hdr['NAXIS2'], hdr['NAXIS1'] = imshape
                        hdu.data = hdu.data.reshape(imshape)

                # Obtain the unique layer name: filter name, extension name, or
                # just the HDU index
                layer = hdr.get('FILTER') or \
                    hdr.get('EXTNAME') or str(i + 1)
                layer_base, layer_no = layer, 1
                while layer in layers:
                    layer = '{}.{}'.format(layer_base, layer_no)
                    layer_no += 1
                layers.append(layer)

                # When importing multiple HDUs, add layer name to data file
                # name; keep the original file extension
                if len(fits) > 1 and layer:
                    name = append_suffix(group_name, '.' + layer)

                if i and primary_header:
                    # Copy primary header cards to extension header
                    h = primary_header.copy()
                    for kw in hdr:
                        if kw not in ('COMMENT', 'HISTORY'):
                            try:
                                del h[kw]
                            except KeyError:
                                pass
                    hdr.update(h)

                # Convert DATEOBS (sometimes used) to DATE-OBS (standard)
                if 'DATE-OBS' not in hdr:
                    try:
                        hdr['DATE-OBS'] = hdr['DATEOBS']
                    except KeyError:
                        pass
                    else:
                        try:
                            hdr.comments['DATE-OBS'] = hdr.comments['DATEOBS']
                        except KeyError:
                            pass

                # Remove AMD* astrometric parameters, which are incorrectly
                # interpreted by Astropy/WCSLib
                expr = re.compile(r'AMD[XY]\d+$')
                for kw in list(hdr.keys()):
                    if expr.match(kw):
                        del hdr[kw]

                all_data_files.append(create_data_file(
                    adb, name, root, hdu.data, hdr, provider_id, asset_path,
                    'FITS', asset_metadata, layer, duplicates, session_id,
                    group_name=group_name, group_order=i,
                    allow_duplicate_group_name=i > 0))

    except errors.AfterglowError:
        raise
    except Exception:
        # Non-FITS file; try importing all color planes with Pillow and rawpy
        exif = None
        channels = []
        asset_type = None

        if PILImage is not None:
            # noinspection PyBroadException
            try:
                fp.seek(0)
                with PILImage.open(fp) as im:
                    asset_type = im.format
                    asset_metadata['image_mode'] = im.mode
                    width, height = im.size
                    band_names = im.getbands()
                    asset_metadata['layers'] = len(band_names)
                    if len(band_names) > 1:
                        bands = im.split()
                    else:
                        bands = (im,)
                    channels = [
                        (band_name, numpy.frombuffer(
                            band.tobytes(), numpy.uint8).reshape(
                            [height, width]))
                        for band_name, band in zip(band_names, bands)]
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
                    asset_type = str(im.raw_type)
                    asset_metadata['image_mode'] = im.color_desc.decode(
                        'ascii')
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
                hdr['EXPOSURE'] = (exif['ExposureTime'],
                                   '[s] Integration time')
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

        for i, (layer, data) in enumerate(channels):
            if layer:
                hdr['FILTER'] = (layer, 'Filter name')

            if len(channels) > 1 and layer:
                name = append_suffix(group_name, '.' + layer)

            # Store FITS image bottom to top
            all_data_files.append(create_data_file(
                adb, name, root, data[::-1], hdr, provider_id, asset_path,
                asset_type, asset_metadata, layer, duplicates, session_id,
                group_name=group_name, group_order=i,
                allow_duplicate_group_name=i > 0))

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
                'x', 'X must be positive and not greater than image width',
                422)
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
                'Height must be positive and less than or equal to {:d}'
                .format(height - y0), 422)
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
        return pyfits.open(
            get_data_file_path(user_id, file_id), mode, memmap=False)
    except Exception:
        raise UnknownDataFileError(file_id=file_id)


def get_data_file_data(user_id: Optional[int], file_id: int) \
        -> Tuple[Union[numpy.ndarray, numpy.ma.MaskedArray], pyfits.Header]:
    """
    Return FITS file data and header for a data file with the given ID; handles
    masked images

    :param user_id: current user ID (None if user auth is disabled)
    :param file_id: data file ID

    :return: tuple (data, hdr); if the underlying FITS file contains a mask in
        an extra image HDU, it is converted into
        a :class:`numpy.ma.MaskedArray` instance
    """
    with get_data_file_fits(user_id, file_id) as fits:
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
                data = numpy.ma.masked_array(
                    fits[0].data, fits[1].data.astype(bool))
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
    data = get_data_file_data(user_id, file_id)[0][::-1]
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
                        fmt: Optional[str] = None) -> bytes:
    """
    Return FITS file data for data file with the given ID

    :param user_id: current user ID (None if user auth is disabled)
    :param file_id: data file ID
    :param fmt: image export format: "FITS" or any supported by Pillow;
        default: use the original import format

    :return: data file bytes
    """
    if not fmt:
        # If omitted, use the original file format from asset_type
        fmt = get_data_file(user_id, file_id).asset_type or 'FITS'

    if fmt == 'FITS':
        try:
            with open(get_data_file_path(user_id, file_id), 'rb') as f:
                return f.read()
        except Exception:
            raise UnknownDataFileError(file_id=file_id)

    if PILImage is None:
        raise DataFileExportError(
            reason='Server does not support image export')

    # Export image via Pillow using the specified mode
    data = get_data_file_uint8(user_id, file_id)
    buf = BytesIO()
    try:
        PILImage.fromarray(data).save(buf, format=fmt)
    except Exception as e:
        raise DataFileExportError(reason=str(e))
    return buf.getvalue()


def get_data_file_group_bytes(user_id: Optional[int], group_name: str,
                              fmt: Optional[str] = None,
                              mode: Optional[str] = None) -> bytes:
    """
    Return data combined from a data file group in the original format,
    suitable for exporting to data provider

    :param user_id: current user ID (None if user auth is disabled)
    :param group_name: data file group name
    :param fmt: image export format: "FITS" or any supported by Pillow;
        default: use the original import format
    :param mode: for non-FITS formats, Pillow image mode
        (https://pillow.readthedocs.io/en/stable/handbook/concepts.html);
        default: use the original import mode or guess from the number of files
        in the group: 1 -> L, 3 -> RGB, 4 -> RGBA

    :return: data file bytes
    """
    with get_data_file_db(user_id) as adb:
        data_file_ids, data_file_types, data_file_formats, data_file_modes = \
            zip(
                *[(df.id, df.type, df.asset_type,
                   df.asset_metadata.get('image_mode')
                   if getattr(df, 'asset_metadata', None) else None)
                  for df in adb.query(DbDataFile)
                  .filter(DbDataFile.group_name == group_name)
                  .order_by(DbDataFile.group_order)])
    n = len(data_file_ids)
    if not n:
        raise UnknownDataFileGroupError(group_name=group_name)

    if not fmt:
        if not all(data_file_formats) or len(set(data_file_formats)) != 1:
            raise DataFileExportError(
                reason='Undefined or inconsistent file types in the group; '
                'please specify the output format explicitly')
        fmt = data_file_formats[0]

    buf = BytesIO()
    if fmt == 'FITS':
        # Assemble individual single-HDU data files into a single multi-HDU
        # FITS
        fits = pyfits.HDUList()
        for file_id, hdu_type in zip(data_file_ids, data_file_types):
            with open(get_data_file_path(user_id, file_id), 'rb') as f:
                data = f.read()
            if hdu_type == 'image':
                fits.append(pyfits.ImageHDU.fromstring(data))
            else:
                fits.append(pyfits.BinTableHDU.fromstring(data))
        fits.writeto(buf, output_verify='silentfix+ignore')
    elif PILImage is None:
        raise DataFileExportError(
            reason='Server does not support image export')
    else:
        # Export image via Pillow using the specified mode
        if not mode:
            # Try to use the original mode
            if all(data_file_modes) and len(set(data_file_modes)) == 1:
                mode = data_file_modes[0]
            # Use default mode depending on the number of files in the group
            elif n == 1:
                mode = 'L'
            elif n == 3:
                mode = 'RGB'
            elif n == 4:
                mode = 'RGBA'
            else:
                raise DataFileExportError(
                    reason="Don't know how to export a group of {:d} images"
                    .format(n))
        if n > 1:
            if mode not in PILImage.MODES:
                raise DataFileExportError(
                    reason='Unsupported image export mode "{}"'.format(mode))
        if any(hdu_type != 'image' for hdu_type in data_file_types):
            raise DataFileExportError(
                reason='Cannot export non-image data files')
        try:
            if n > 1:
                im = PILImage.merge(
                    mode,
                    [PILImage.fromarray(get_data_file_uint8(user_id, file_id))
                     for file_id in data_file_ids])
            else:
                im = PILImage.fromarray(get_data_file_uint8(
                    user_id, data_file_ids[0]))
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
    with get_data_file_db(user_id) as adb:
        try:
            db_data_file = adb.query(DbDataFile).get(int(file_id))
        except ValueError:
            db_data_file = None
        if db_data_file is None:
            raise UnknownDataFileError(file_id=file_id)

        # Convert to data model object
        return DataFile(db_data_file)


def get_data_file_group(user_id: Optional[int], group_name: str) \
        -> TList[DataFile]:
    """
    Return data file objects belonging to the given group

    :param user_id: current user ID (None if user auth is disabled)
    :param group_name: data file group name

    :return: data file objects sorted by group_order
    """
    with get_data_file_db(user_id) as adb:
        return [DataFile(db_data_file)
                for db_data_file in adb.query(DbDataFile)
                .filter(DbDataFile.group_name == group_name)
                .order_by(DbDataFile.group_order)]


def query_data_files(user_id: Optional[int], session_id: Optional[int]) \
        -> TList[DataFile]:
    """
    Return data file objects matching the given criteria

    :param user_id: current user ID (None if user auth is disabled)
    :param session_id: only return data files belonging to the given session

    :return: list of data file objects
    """
    with get_data_file_db(user_id) as adb:
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
                      width: Optional[int] = None,
                      height: Optional[int] = None,
                      pixel_value: float = 0,
                      files: Optional[TDict[str, bytes]] = None) \
        -> TList[DataFile]:
    """
    Create, import, or upload data files defined by request parameters:
        `provider_id` = None:
            `files` = None: create empty data file defined by `width`,
                `height`, and `pixel_value`
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
    root = get_root(user_id)
    all_data_files = []
    with get_data_file_db(user_id) as adb:
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
                if not app.config.get('DATA_FILE_UPLOAD'):
                    raise DataFileUploadNotAllowedError()
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
                                asset.path)[0]], [])
                    return import_data_file(
                        adb, root, provider_id, asset.path, asset.metadata,
                        BytesIO(provider.get_asset_data(asset.path)),
                        name or asset.name if len(path) == 1 else asset.name,
                        duplicates, session_id=session_id)

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
    :param data_file: data_file object containing updated parameters: name,
        session ID, group name, or group order
    :param force: if set, flag the data file as modified even if no fields were
        changed (e.g. if updating header or pixel data)

    :return: updated field cal object
    """
    with get_data_file_db(user_id) as adb:
        db_data_file = adb.query(DbDataFile).get(data_file_id)
        if db_data_file is None:
            raise UnknownDataFileError(file_id=data_file_id)

        modified = fields_changed = force
        for key, val in data_file.to_dict().items():
            if key not in ('name', 'session_id', 'group_name', 'group_order',
                           'data_provider', 'asset_path'):
                continue
            if val != getattr(db_data_file, key):
                setattr(db_data_file, key, val)
                fields_changed = True
                if key in ('name', 'session_id'):
                    modified = True
        if modified:
            db_data_file.modified = True
        if fields_changed:
            try:
                adb.flush()
                data_file = DataFile(db_data_file)
                adb.commit()
            except Exception:
                adb.rollback()
                raise
        else:
            data_file = DataFile(db_data_file)

    return data_file


def update_data_file_asset(user_id: Optional[int], data_file_id: int,
                           provider_id: str, asset_path: str,
                           asset_metadata: dict, name: str) -> None:
    """
    Link data file to a new asset; called after exporting data file to asset

    :param user_id: current user ID (None if user auth is disabled)
    :param data_file_id: data file ID to update
    :param provider_id: data provider ID/name
    :param asset_path: data provider asset path
    :param asset_metadata: data provider asset metadata
    :param name: new data file name
    """
    with get_data_file_db(user_id) as adb:
        db_data_file = adb.query(DbDataFile).get(data_file_id)
        if db_data_file is None:
            raise UnknownDataFileError(file_id=data_file_id)

        try:
            db_data_file.data_provider = provider_id
            db_data_file.asset_path = asset_path
            db_data_file.asset_metadata = asset_metadata
            db_data_file.name = name
            db_data_file.modified = False
            adb.commit()
        except Exception:
            adb.rollback()
            raise


def update_data_file_group_asset(user_id: Optional[int], group_name: str,
                                 provider_id: str, asset_path: str,
                                 asset_metadata: dict, name: str) -> None:
    """
    Link data file group to a new asset; called after exporting group to asset

    :param user_id: current user ID (None if user auth is disabled)
    :param group_name: data file group name to update
    :param provider_id: data provider ID/name
    :param asset_path: data provider asset path
    :param asset_metadata: data provider asset metadata
    :param name: new data file name
    """
    with get_data_file_db(user_id) as adb:
        db_data_files = adb.query(DbDataFile) \
            .filter(DbDataFile.group_name == group_name)
        if not db_data_files.count():
            raise UnknownDataFileGroupError(group_name=group_name)

        try:
            for db_data_file in db_data_files:
                db_data_file.data_provider = provider_id
                db_data_file.asset_path = asset_path
                db_data_file.asset_metadata = asset_metadata
                db_data_file.name = name
                db_data_file.modified = False
            adb.commit()
        except Exception:
            adb.rollback()
            raise


def delete_data_file(user_id: Optional[int], id: int) -> None:
    """
    Remove the given data file from database and delete all associated disk
    files

    :param user_id: current user ID (None if user auth is disabled)
    :param id: data file ID
    """
    root = get_root(user_id)
    with get_data_file_db(user_id) as adb:
        db_data_file = adb.query(DbDataFile).get(id)
        if db_data_file is None:
            raise UnknownDataFileError(file_id=id)
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
            app.logger.warning(
                'Error removing data file "%s" (ID %d) [%s]',
                filename, id,
                e.message if hasattr(e, 'message') and e.message
                else ', '.join(str(arg) for arg in e.args) if e.args
                else e)


def get_session(user_id: Optional[int], session_id: Union[int, str]) \
        -> Session:
    """
    Return session object with the given ID or name

    :param user_id: current user ID (None if user auth is disabled)
    :param session_id: session ID

    :return: session object
    """
    with get_data_file_db(user_id) as adb:
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
    with get_data_file_db(user_id) as adb:
        return [Session(db_session) for db_session in adb.query(DbSession)]


def create_session(user_id: Optional[int], session: Session) -> Session:
    """
    Create a new session with the given parameters

    :param user_id: current user ID (None if user auth is disabled)
    :param session: session object containing all relevant parameters

    :return: new session object
    """
    with get_data_file_db(user_id) as adb:
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
    with get_data_file_db(user_id) as adb:
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
    with get_data_file_db(user_id) as adb:
        try:
            db_session = adb.query(DbSession).get(session_id)
            if db_session is None:
                raise UnknownSessionError(id=session_id)

            file_ids = [data_file.id for data_file in db_session.data_files]

            adb.delete(db_session)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

    for file_id in file_ids:
        delete_data_file(user_id, file_id)
