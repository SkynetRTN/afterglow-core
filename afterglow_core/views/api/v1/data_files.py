"""
Afterglow Core: API v1 data file views
"""

import json
import astropy.io.fits as pyfits
import os
import tempfile
import subprocess
import shutil
from io import BytesIO

import numpy
from flask import request, Response
from astropy.wcs import WCS
from skylib.calibration.background import estimate_background
from skylib.sonification import sonify_image

from .... import app, json_response, auth, errors
from ....schemas.api.v1 import DataFileSchema, SessionSchema
from ....errors.data_provider import UnknownDataProviderError
from ....errors.data_file import (
    UnknownDataFileError, CannotImportFromCollectionAssetError)
from ....resources import data_providers
from ....resources.data_files import (
    SqlaSession, SqlaDataFile, get_data_file_db, get_root, get_session_id,
    create_data_file, import_data_file, remove_data_file, get_data_file,
    get_data_file_path, get_subframe, get_data_file_data, make_data_response)
from . import url_prefix


resource_prefix = url_prefix + 'data-files/'


@app.route(resource_prefix[:-1], methods=['GET', 'POST'])
@app.route(resource_prefix + '<int:id>', methods=['GET', 'PUT', 'DELETE'])
@auth.auth_required('user')
def data_files(id=None):
    """
    Return, create, update, or delete data file(s)

    GET /data-files?session_id=...
        - return a list of all user's data files associated with the given
          session or with the default anonymous session if unspecified

    GET /data-files/[id]
        - return a single data file with the given ID

    POST /data-files?name=...&width=...&height=...&pixel_value=...session_id=...
        - create a single data file of the given width and height, with data
          values set to pixel_value (0 by default); associate with the given
          session (anonymous if not set)

    POST /data-files?name=...&session_id=...
        - import data file from the request body to the given session

    POST /data-files?provider_id=...&path=...&duplicates=...&recurse=...
                     session_id=...
        - import file(s) to the given session (anonymous by default) from a data
          provider asset at the given path; if the path identifies a collection
          asset of a browseable data provider, import all non-collection child
          assets (and, optionally, all collection assets too if recurse=1);
          the `duplicates` argument defines the import behavior in the case when
          a certain non-collection asset was already imported: "ignore"
          (default) = skip already imported assets, "overwrite" = re-import,
          "append" = always create a new data file; multiple asset paths can
          be passed as a JSON list

    PUT /data-files/[id]?name=...&session_id=...
        - rename data file or reassign to different session

    DELETE /data-files/[id]
        - delete the given data file

    :param int id: data file ID for GET and DELETE requests

    :return:
        GET: JSON response containing either the list of serialized data file
            objects when no id supplied or a single data file otherwise
        POST: JSON-serialized list of the new data files
        PUT: JSON-serialized updated data file
        DELETE: empty response
    :rtype: flask.Response | str
    """
    root = get_root(auth.current_user.id)
    adb = get_data_file_db(auth.current_user.id)

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
            # List all data files for the given session
            return json_response([
                    DataFileSchema(data_file)
                    for data_file in adb.query(SqlaDataFile).filter(
                        SqlaDataFile.session_id == get_session_id(adb))])

        # Return specific data file resource
        return json_response(DataFileSchema(data_file))

    if request.method == 'POST':
        # Create data file(s)
        all_data_files = []

        try:
            session_id = get_session_id(adb)

            import_params = request.args.to_dict()
            provider_id = import_params.pop('provider_id', None)
            duplicates = import_params.pop('duplicates', 'ignore')
            files = request.files

            if provider_id is None and not files:
                # Create an empty image data file
                try:
                    width = int(import_params['width'])
                    if width < 1:
                        raise errors.ValidationError(
                            'width', 'Width must be positive', 422)
                except KeyError:
                    raise errors.MissingFieldError('width')
                except ValueError:
                    raise errors.ValidationError(
                        'width', 'Width must be a positive integer')
                try:
                    height = int(import_params['height'])
                    if height < 1:
                        raise errors.ValidationError(
                            'height', 'Height must be positive', 422)
                except KeyError:
                    raise errors.MissingFieldError('height')
                except ValueError:
                    raise errors.ValidationError(
                        'width', 'Width must be a positive integer')

                data = numpy.zeros([height, width], dtype=numpy.float32)
                if import_params.get('pixel_value') is not None:
                    try:
                        pixel_value = float(import_params['pixel_value'])
                    except ValueError:
                        raise errors.ValidationError(
                            'pixel_value', 'Pixel value must be a number')
                    else:
                        # noinspection PyPropertyAccess
                        data += pixel_value

                all_data_files.append(create_data_file(
                    adb, import_params.get('name'), root, data,
                    duplicates='append', session_id=session_id))
            elif provider_id is None:
                # Data file upload: get from multipart/form-data; use filename
                # for the 2nd and subsequent files or if the "name" parameter
                # is not provided
                for i, (name, file) in enumerate(files.items()):
                    all_data_files += import_data_file(
                        adb, root, None, None, import_params,
                        BytesIO(file.read()),
                        name if i else import_params.get('name') or name,
                        duplicates='append', session_id=session_id)
            else:
                # Import data file
                import_params = request.args.to_dict()
                provider_id = import_params.pop('provider_id', None)
                duplicates = import_params.pop('duplicates', 'ignore')
                if provider_id is None:
                    # Data file upload: get data from request body
                    all_data_files += import_data_file(
                        adb, root, None, None, import_params,
                        BytesIO(request.data),
                        import_params.get('name'),
                        duplicates, session_id=session_id)
                else:
                    # Import data from the given data provider
                    try:
                        asset_path = import_params.pop('path')
                    except KeyError:
                        raise errors.MissingFieldError('path')

                    try:
                        provider = data_providers.providers[provider_id]
                    except KeyError:
                        raise UnknownDataProviderError(id=provider_id)
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
                            asset.name, duplicates, session_id=session_id)

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
        session_id = get_session_id(adb)
        if name and name != data_file.name or \
                session_id != data_file.session_id:
            try:
                if name:
                    data_file.name = name
                data_file.session_id = session_id
                data_file.modified = True
                adb.commit()
            except Exception:
                adb.rollback()
                raise

        return json_response(DataFileSchema(data_file))

    if request.method == 'DELETE':
        # Delete data file
        try:
            remove_data_file(adb, root, id)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response()


@app.route(resource_prefix + '<int:id>/header', methods=['GET', 'PUT'])
@auth.auth_required('user')
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
    :rtype: flask.Response
    """
    if request.method == 'GET':
        hdr = get_data_file(auth.current_user.id, id)[1]
    else:
        with pyfits.open(get_data_file_path(auth.current_user.id, id),
                         'update') as fits:
            hdr = fits[0].header
            for name, val in request.args.items():
                hdr[name] = val

        adb = get_data_file_db(auth.current_user.id)
        try:
            data_file = adb.query(SqlaDataFile).get(id)
            data_file.modified = True
            adb.commit()
        except Exception:
            adb.rollback()
            raise

    return json_response([
        dict(key=key, value=value, comment=hdr.comments[i])
        for i, (key, value) in enumerate(hdr.items())])


@app.route(resource_prefix + '<int:id>/wcs', methods=['GET', 'PUT'])
@auth.auth_required('user')
def data_files_wcs(id):
    """
    Return or update data file WCS

    GET /data-files/[id]/wcs

    PUT /data-files/[id]/wcs?keyword=value...
        - must contain all relevant WCS info; the previous WCS (CDn_m, PCn_m,
          CDELTn, and CROTAn) is removed

    :param int id: data file ID

    :return: JSON-serialized structure
        [{"key": key, "value": value, "comment": comment}, ...]
        containing the data file header cards pertaining to the WCS in the order
        they are returned by WCSLib; empty if the existing or updated FITS
        header has no valid WCS info
    :rtype: flask.Response
    """
    if request.method == 'GET':
        hdr = get_data_file(auth.current_user.id, id)[1]
    else:
        with pyfits.open(get_data_file_path(auth.current_user.id, id),
                         'update') as fits:
            hdr = fits[0].header
            for name, val in request.args.items():
                if val is None:
                    try:
                        del hdr[name]
                    except KeyError:
                        pass
                else:
                    hdr[name] = val

    wcs_hdr = None
    # noinspection PyBroadException
    try:
        wcs = WCS(hdr, relax=True)
        if wcs.has_celestial:
            wcs_hdr = wcs.to_header(relax=True)
    except Exception:
        pass

    adb = get_data_file_db(auth.current_user.id)
    try:
        data_file = adb.query(SqlaDataFile).get(id)
        data_file.modified = True
        adb.commit()
    except Exception:
        adb.rollback()
        raise

    if wcs_hdr:
        return json_response([
            dict(key=key, value=value, comment=wcs_hdr.comments[i])
            for i, (key, value) in enumerate(wcs_hdr.items())])

    return json_response([])


@app.route(resource_prefix + '<int:id>/phot_cal', methods=['GET', 'PUT'])
@auth.auth_required('user')
def data_files_phot_cal(id):
    """
    Return or update data file photometric calibration (zero point and error)

    GET /data-files/[id]/phot_cal

    PUT /data-files/[id]/phot_cal?m0=...[&m0_err=...]

    :param int id: data file ID

    :return: JSON-serialized structure {"m0": ..., "m0_err": ...} containing
        photometric zero point and its error, if any; empty structure means
        no calibration data available
    :rtype: flask.Response
    """
    if request.method == 'GET':
        phot_cal = {}
        with pyfits.open(get_data_file_path(auth.current_user.id, id),
                         'readonly') as fits:
            hdr = fits[0].header
            try:
                phot_cal['m0'] = float(hdr['PHOT_M0'])
            except (KeyError, ValueError):
                pass

            try:
                phot_cal['m0_err'] = float(hdr['PHOT_M0E'])
            except (KeyError, ValueError):
                pass
    else:
        with pyfits.open(get_data_file_path(auth.current_user.id, id),
                         'update') as fits:
            phot_cal = {}
            try:
                phot_cal['m0'] = float(request.args['m0'])
            except KeyError:
                pass
            except ValueError:
                raise errors.ValidationError(
                    'm0', 'Floating-point m0 expected')
            try:
                phot_cal['m0_err'] = float(request.args['m0_err'])
                if phot_cal['m0_err'] <= 0:
                    raise ValueError()
            except KeyError:
                pass
            except ValueError:
                raise errors.ValidationError(
                    'm0_err', 'Positive floating-point m0_err expected')

            hdr = fits[0].header
            try:
                hdr['PHOT_M0'] = phot_cal['m0']
            except KeyError:
                try:
                    del hdr['PHOT_M0']
                except KeyError:
                    pass
            try:
                hdr['PHOT_M0E'] = phot_cal['m0_err']
            except KeyError:
                try:
                    del hdr['PHOT_M0E']
                except KeyError:
                    pass

        adb = get_data_file_db(auth.current_user.id)
        try:
            data_file = adb.query(SqlaDataFile).get(id)
            data_file.modified = True
            adb.commit()
        except Exception:
            adb.rollback()
            raise

    return json_response(phot_cal)


@app.route(resource_prefix + '<int:id>/hist')
@auth.auth_required('user')
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
    root = get_root(auth.current_user.id)

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
            data = get_data_file(auth.current_user.id, id)[0]
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
@auth.auth_required('user')
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
        return make_data_response(get_subframe(auth.current_user.id, id))
    except errors.AfterglowError:
        raise
    except Exception:
        raise UnknownDataFileError(id=id)


@app.route(resource_prefix + '<int:id>/fits')
@auth.auth_required('user')
def data_files_fits(id):
    """
    Return the whole data file as a FITS file

    GET /data-files/[id]/fits

    Depending on the request headers (Accept and Accept-Encoding), the FITS
    file is returned either as a gzipped or uncompressed (default) FITS.

    [Accept-Encoding:]
    [Accept-Encoding: identity]
    -> (uncompressed FITS)
    Content-Type: image/fits

    Accept-Encoding: gzip
    -> (compressed FITS)
    Content-Type: image/fits
    Content-Encoding: gzip

    :param int id: data file ID

    :return: depending on the Accept and Accept-Encoding HTTP headers (see
        above), either the gzipped or uncompressed FITS file data
    :rtype: flask.Response
    """
    return make_data_response(get_data_file_data(auth.current_user.id, id))


@app.route(resource_prefix + '<int:id>/sonification')
@auth.auth_required('user')
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
        pixels = get_subframe(auth.current_user.id, id)
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

    adb = get_data_file_db(auth.current_user.id)
    df = adb.query(SqlaDataFile).get(id)
    height, width = pixels.shape
    if width != df.width or height != df.height:
        # Sonifying a subimage; estimate background from the whole image first,
        # then supply a cutout of background and RMS to sonify_image()
        try:
            bkg_scale = float(args.pop('bkg_scale', 1/64))
        except ValueError:
            bkg_scale = 1/64
        full_img = get_data_file(auth.current_user.id, id)[0]
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


@app.route(url_prefix + 'sessions', methods=['GET', 'POST'])
@app.route(url_prefix + 'sessions/<id>', methods=['GET', 'PUT', 'DELETE'])
@auth.auth_required('user')
def sessions(id=None):
    """
    Return, create, update, or delete session(s)

    GET /sessions
        - return all user's sessions

    GET /sessions/[id]
        - return the given session info by ID or name

    POST /sessions?name=...&data=...
        - create a new session with the given name and optional user data

    PUT /sessions/[id]?name=...&data=...
        - rename session with the given ID or name or change session data

    DELETE /sessions/[id]
        - delete the given session

    :param int | str id: session ID or name

    :return:
        GET: JSON response containing the list of serialized session objects
            when no id/name supplied or a single session otherwise
        POST: JSON-serialized new session object
        PUT: JSON-serialized updated session object
        DELETE: empty response
    :rtype: flask.Response | str
    """
    adb = get_data_file_db(auth.current_user.id)

    if id is not None:
        # When getting, updating, or deleting specific session, check that it
        # exists
        session = adb.query(SqlaSession).get(id)
        if session is None:
            session = adb.query(SqlaSession).filter(
                SqlaSession.name == id).one_or_none()
        if session is None:
            raise errors.ValidationError(
                'id', 'Unknown session "{}"'.format(id), 404)
    else:
        session = None

    if request.method == 'GET':
        if session is None:
            # List all sessions
            return json_response(
                [SessionSchema(session) for session in adb.query(SqlaSession)])

        # Return specific session resource
        return json_response(SessionSchema(session))

    if request.method == 'POST':
        # Create session
        if not request.args.get('name'):
            raise errors.MissingFieldError('name')
        try:
            session = SqlaSession(**request.args.to_dict())
            adb.add(session)
            adb.commit()
        except Exception:
            adb.rollback()
            raise
        return json_response(SessionSchema(session), 201)

    if request.method == 'PUT':
        # Rename session
        try:
            for name, val in request.args.items():
                setattr(session, name, val)
            adb.commit()
        except Exception:
            adb.rollback()
            raise
        return json_response(SessionSchema(session))

    if request.method == 'DELETE':
        # Delete session and all its data files
        root = get_root(auth.current_user.id)
        try:
            for file_id in [data_file.id for data_file in session.data_files]:
                remove_data_file(adb, root, file_id)
            adb.query(SqlaSession).filter(
                SqlaSession.id == session.id).delete()
            adb.commit()
        except Exception:
            adb.rollback()
            raise
        return json_response()
