"""
Afterglow Core: API v1 data file views
"""

import sys
import os
import astropy.io.fits as pyfits
import gzip
from io import BytesIO
from datetime import datetime
from typing import Optional, Union

import numpy
from flask import Response, request
from astropy.wcs import WCS

from skylib.extraction import histogram

from .... import app, json_response, auth, errors
from ....models import DataFile, Session
from ....errors.data_file import UnknownDataFileError
from ....resources.data_files import *
from ....schemas.api.v1 import DataFileSchema, SessionSchema
from . import url_prefix


resource_prefix = url_prefix + 'data-files/'


def make_data_response(data: Union[bytes, numpy.ndarray, numpy.ma.MaskedArray],
                       mimetype: Optional[str] = None,
                       status_code: int = 200) -> Response:
    """
    Initialize a Flask response object returning the binary data array

    Depending on the request headers (Accept and Accept-Encoding), the data are
    returned either as an optionally gzipped binary stream or as a JSON list.

    :param data: data to send to the client
    :param mimetype: optional MIME type of the data; automatically guessed
        if not set
    :param status_code: optional HTTP status code; defaults to 200 - OK

    :return: Flask response object
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
            if isinstance(data, numpy.ma.MaskedArray) and \
                    data.fill_value != numpy.nan:
                # Replace masked values with NaNs
                data = data.filled(numpy.nan)
            # Make sure data are in little-endian byte order before sending
            # over the net
            if data.dtype.byteorder == '>' or \
                    data.dtype.byteorder == '=' and sys.byteorder == 'big':
                data = data.astype(data.dtype.newbyteorder('<'))
            data = data.tobytes()
            if not mimetype:
                mimetype = 'application/octet-stream'
        elif not mimetype:
            # Sending FITS file
            mimetype = 'image/fits'
        if allow_gzip:
            s = BytesIO()
            with gzip.GzipFile(fileobj=s, mode='wb') as f:
                f.write(data)
            data = s.getvalue()
            headers = [('Content-Encoding', 'gzip')]
        else:
            headers = []
        headers.append(('Content-Length', str(len(data))))
        return Response(data, status_code if data else 204, headers, mimetype)

    if allow_json and is_array:
        return json_response(data.tolist(), status_code)

    # Could not send data in any of the formats supported by the client
    raise errors.NotAcceptedError(accepted_mimetypes=accepted_mimetypes)


@app.route(resource_prefix[:-1], methods=['GET', 'POST'])
@auth.auth_required('user')
def data_files() -> Response:
    """
    Return or create data files

    GET /data-files?session_id=...
        - return a list of all user's data files associated with the given
          session or with the default anonymous session if unspecified

    POST /data-files?name=...&width=...&height=...&pixel_value=...
        [&session_id=...]
        - create a single data file of the given width and height, with data
          values set to pixel_value (0 by default); associate with the given
          session (anonymous if not set)

    POST /data-files?name=...[&session_id=...]
        - import data file from multipart/form-data to the given session

    POST /data-files?provider_id=...&path=...&duplicates=...&recurse=...
                     [&session_id=...]
        - import file(s) to the given session (anonymous by default) from
          a data provider asset at the given path; if the path identifies
          a collection asset of a browsable data provider, import all
          non-collection child assets (and, optionally, all collection assets
          too if recurse=1); the `duplicates` argument defines the import
          behavior in the case when a certain non-collection asset was already
          imported: "ignore" (default) = skip already imported assets,
          "overwrite" = re-import, "append" = always create a new data file;
          multiple asset paths can be passed as a JSON list

    POST /data-files?name=...&file_id=...[&session_id=...]
        - duplicate the given data file

    :return:
        GET: JSON response containing the list of serialized data file objects
            matching the given parameters
        POST: JSON-serialized list of the new data file(s)
    """
    if request.method == 'GET':
        # List all data files for the given session
        return json_response([
            DataFileSchema(df)
            for df in query_data_files(
                request.user.id, request.args.get('session_id'))])

    if request.method == 'POST':
        # Create data file(s)
        res = [
            DataFileSchema(df)
            for df in import_data_files(
                request.user.id, files=request.files,
                **request.args.to_dict())]

        return json_response(res, 201 if res else 200)


@app.route(resource_prefix + '<int:id>', methods=['GET', 'PUT', 'DELETE'])
@auth.auth_required('user')
def data_file(id: int) -> Response:
    """
    Return, update, or delete data file

    GET /data-files/[id]
        - return a single data file with the given ID

    PUT /data-files/[id]?name=...&session_id=...
        - rename data file or reassign to different session

    DELETE /data-files/[id]
        - delete the given data file

    :param id: data file ID

    :return:
        GET, PUT: JSON-serialized data file
        DELETE: empty response
    """
    if request.method == 'GET':
        # Return specific data file resource
        return json_response(DataFileSchema(get_data_file(
            request.user.id, id)))

    if request.method == 'PUT':
        # Update data file
        return json_response(DataFileSchema(update_data_file(
            request.user.id, id,
            DataFile(DataFileSchema(**request.args.to_dict()),
                     only=list(request.args.keys())))))

    if request.method == 'DELETE':
        # Delete data file
        delete_data_file(request.user.id, id)
        return json_response()


@app.route(resource_prefix + '<int:id>/header', methods=['GET', 'PUT'])
@auth.auth_required('user')
def data_files_header(id: int) -> Response:
    """
    Return or update data file header

    GET /data-files/[id]/header

    PUT /data-files/[id]/header?keyword=value&keyword=[value, "comment"]...

    :param id: data file ID

    :return: JSON-serialized structure
        [{"key": key, "value": value, "comment": comment}, ...]
        containing the data file header cards in the order they appear in the
        underlying FITS file header
    """
    if request.method == 'GET':
        hdr = get_data_file_data(request.user.id, id)[1]
    else:
        with pyfits.open(get_data_file_path(request.user.id, id),
                         'update', memmap=False) as fits:
            hdr = fits[0].header
            modified = False
            for name, val in request.args.items():
                if val is None:
                    try:
                        del hdr[name]
                    except KeyError:
                        pass
                    else:
                        modified = True
                else:
                    if hasattr(val, '__len__'):
                        if hdr.get(name) != val[0]:
                            hdr[name] = tuple(val)
                            modified = True
                    elif hdr.get(name) != val:
                        hdr[name] = val
                        modified = True

        if modified:
            update_data_file(
                request.user.id, id, DataFile(only=[]), force=True)

    return json_response([
        dict(key=key, value=value, comment=hdr.comments[i])
        for i, (key, value) in enumerate(hdr.items())])


@app.route(resource_prefix + '<int:id>/wcs', methods=['GET', 'PUT'])
@auth.auth_required('user')
def data_files_wcs(id: int) -> Response:
    """
    Return or update data file WCS

    GET /data-files/[id]/wcs

    PUT /data-files/[id]/wcs?keyword=value...
        - must contain all relevant WCS info; the previous WCS (CDn_m, PCn_m,
          CDELTn, and CROTAn) is removed

    :param id: data file ID

    :return: JSON-serialized structure
        [{"key": key, "value": value, "comment": comment}, ...]
        containing the data file header cards pertaining to the WCS
        in the order they are returned by WCSLib; empty if the existing
        or updated FITS header has no valid WCS info
    """
    if request.method == 'GET':
        hdr = get_data_file_data(request.user.id, id)[1]
    else:
        with pyfits.open(get_data_file_path(request.user.id, id),
                         'update', memmap=False) as fits:
            hdr = fits[0].header
            modified = False
            for name, val in request.args.items():
                if val is None:
                    try:
                        del hdr[name]
                    except KeyError:
                        pass
                    else:
                        modified = True
                else:
                    if hasattr(val, '__len__'):
                        if hdr.get(name) != val[0]:
                            hdr[name] = tuple(val)
                            modified = True
                    elif hdr.get(name) != val:
                        hdr[name] = val
                        modified = True

        if modified:
            update_data_file(
                request.user.id, id, DataFile(only=[]), force=True)

    wcs_hdr = None
    # noinspection PyBroadException
    try:
        wcs = WCS(hdr, relax=True)
        if wcs.has_celestial:
            wcs_hdr = wcs.to_header(relax=True)
    except Exception:
        pass

    if wcs_hdr:
        return json_response([
            dict(key=key, value=value, comment=wcs_hdr.comments[i])
            for i, (key, value) in enumerate(wcs_hdr.items())])

    return json_response([])


PHOT_CAL_MAPPING = [('PHOT_M0', 'm0'), ('PHOT_M0E', 'm0_err')]


@app.route(resource_prefix + '<int:id>/phot-cal', methods=['GET', 'PUT'])
@auth.auth_required('user')
def data_files_phot_cal(id: int) -> Response:
    """
    Return or update data file photometric calibration (zero point and error)

    GET /data-files/[id]/phot_cal

    PUT /data-files/[id]/phot_cal?m0=...[&m0_err=...]

    :param id: data file ID

    :return: JSON-serialized structure {"m0": ..., "m0_err": ...} containing
        photometric zero point and its error, if any; empty structure means
        no calibration data available
    """
    if request.method == 'GET':
        phot_cal = {}
        with pyfits.open(get_data_file_path(request.user.id, id),
                         'readonly', memmap=False) as fits:
            hdr = fits[0].header
            for field, name in PHOT_CAL_MAPPING:
                try:
                    phot_cal[name] = float(hdr[field])
                except (KeyError, ValueError):
                    pass
    else:
        with pyfits.open(get_data_file_path(request.user.id, id),
                         'update', memmap=False) as fits:
            phot_cal = {}
            try:
                phot_cal['m0'] = (float(request.args['m0']),
                                  'Photometric zero point')
            except KeyError:
                pass
            except ValueError:
                raise errors.ValidationError(
                    'm0', 'Floating-point m0 expected')
            try:
                phot_cal['m0_err'] = (float(request.args['m0_err']),
                                      'Photometric zero point error')
                if phot_cal['m0_err'][0] <= 0:
                    raise ValueError()
            except KeyError:
                pass
            except ValueError:
                raise errors.ValidationError(
                    'm0_err', 'Positive floating-point m0_err expected')

            hdr = fits[0].header
            modified = False
            for field, name in PHOT_CAL_MAPPING:
                try:
                    if hdr.get(field) != phot_cal[name][0]:
                        hdr[field] = phot_cal[name]
                        modified = True
                except KeyError:
                    try:
                        del hdr[field]
                    except KeyError:
                        pass
                    else:
                        modified = True

        if modified:
            update_data_file(
                request.user.id, id, DataFile(only=[]), force=True)

    return json_response(phot_cal)


@app.route(resource_prefix + '<int:id>/hist')
@auth.auth_required('user')
def data_files_hist(id: int) -> Response:
    """
    Return the data file histogram

    GET /data-files/[id]/hist

    The number of bins in the histogram is controlled by the HISTOGRAM_BINS
    configuration variable. It is either the fixed number of bins or a name of
    the method used to adaptively calculate the number of bins required to
    adequately represent the data; see
    `https://docs.scipy.org/doc/numpy/reference/generated/numpy.histogram.html`_

    :param id: data file ID

    :return: JSON-serialized structure
        {"data": [value, value, ...], "min_bin": min_bin, "max_bin": max_bin}
        containing the integer-valued histogram data array and the
        floating-point left and right histogram limits set from the data
    """
    root = get_root(request.user.id)

    # noinspection PyBroadException
    try:
        # First try using the cached histogram
        with pyfits.open(
                os.path.join(root, '{}.fits.hist'.format(id)), 'readonly',
                memmap=False) as hist:
            hdr = hist[0].header
            min_bin, max_bin = hdr['MINBIN'], hdr['MAXBIN']
            data = hist[0].data
            if get_data_file(request.user.id, id).modified_on > \
                    datetime.strptime('%Y-%m-%dT%H:%M:%S.%f', hdr['DATE']):
                raise Exception('Histogram outdated')
    except Exception:
        # Cached histogram not found or outdated, (re)calculate and return
        try:
            data, min_bin, max_bin = histogram(
                get_data_file_data(request.user.id, id)[0],
                app.config['HISTOGRAM_BINS'])

            # Cache histogram and limits
            hist = pyfits.PrimaryHDU(data)
            hist.header['MINBIN'] = min_bin, 'Lower histogram boundary'
            hist.header['MAXBIN'] = max_bin, 'Upper histogram boundary'
            hist.header['DATE'] = (datetime.utcnow().isoformat(),
                                   'UTC timestamp of the histogram')
            hist.writeto(
                os.path.join(root, '{}.fits.hist'.format(id)),
                overwrite=True)
        except errors.AfterglowError:
            raise
        except Exception:
            raise UnknownDataFileError(file_id=id)

    return json_response(
        dict(data=data.tolist(), min_bin=min_bin, max_bin=max_bin))


@app.route(resource_prefix + '<int:id>/pixels')
@auth.auth_required('user')
def data_files_pixels(id: int) -> Response:
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

    :param id: data file ID

    :return: depending on the Accept and Accept-Encoding HTTP headers (see
        above), either the gzipped binary data (application/octet-stream) or
        a JSON list of rows, each one being, in turn, a list of data values
        within the row
    """
    try:
        return make_data_response(get_subframe(
            request.user.id, id,
            x0=request.args.get('x', 1),
            y0=request.args.get('y', 1),
            w=request.args.get('width'),
            h=request.args.get('height')))
    except errors.AfterglowError:
        raise
    except Exception:
        raise UnknownDataFileError(file_id=id)


@app.route(resource_prefix + '<int:id>/fits')
@auth.auth_required('user')
def data_files_fits(id: int) -> Response:
    """
    Return data file as FITS

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

    :param id: data file ID

    :return: depending on the Accept and Accept-Encoding HTTP headers (see
        above), either the gzipped or uncompressed FITS file data
    """
    return make_data_response(get_data_file_bytes(request.user.id, id))


@app.route(resource_prefix + '<int:id>/<fmt>')
@auth.auth_required('user')
def data_files_image(id: int, fmt: str) -> Response:
    """
    Export data file in the given format

    GET /data-files/[id]/[fmt]

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

    :param id: data file ID
    :param fmt: image format supported by Pillow

    :return: depending on the Accept and Accept-Encoding HTTP headers (see
        above), either the gzipped or uncompressed image data
    """
    data = get_data_file_bytes(request.user.id, id, fmt=fmt)
    from PIL import Image  # guaranteed to be available if export succeeded
    return make_data_response(
        data, mimetype=Image.MIME.get(fmt, Image.MIME.get(
            fmt.upper(), 'image')))


@app.route(url_prefix + 'sessions', methods=['GET', 'POST'])
@auth.auth_required('user')
def sessions() -> Response:
    """
    Return or create session(s)

    GET /sessions
        - return all user's sessions

    POST /sessions?name=...&data=...
        - create a new session with the given name and optional user data

    :return:
        GET: JSON response containing the list of serialized session objects
        POST: JSON-serialized new session object
    """
    if request.method == 'GET':
        # List all sessions
        return json_response(
            [SessionSchema(sess)
             for sess in query_sessions(request.user.id)])

    if request.method == 'POST':
        # Create session
        return json_response(SessionSchema(create_session(
            request.user.id,
            Session(SessionSchema(**request.args.to_dict()),
                    only=list(request.args.keys())))), 201)


@app.route(url_prefix + 'sessions/<id>', methods=['GET', 'PUT', 'DELETE'])
@auth.auth_required('user')
def session(id: Union[int, str]) -> Response:
    """
    Return, update, or delete session

    GET /sessions/[id]
        - return the given session info by ID or name

    PUT /sessions/[id]?name=...&data=...
        - rename session with the given ID or name or change session data

    DELETE /sessions/[id]
        - delete the given session

    :param id: session ID or name

    :return:
        GET: JSON response containing the list of serialized session objects
            when no id/name supplied or a single session otherwise
        POST: JSON-serialized new session object
        PUT: JSON-serialized updated session object
        DELETE: empty response
    """
    # When getting, updating, or deleting specific session, check that it
    # exists
    sess = get_session(request.user.id, id)

    if request.method == 'GET':
        # Return specific session resource
        return json_response(SessionSchema(sess))

    if request.method == 'PUT':
        # Update data file
        return json_response(DataFileSchema(update_session(
            request.user.id, id,
            Session(SessionSchema(**request.args.to_dict()),
                    only=list(request.args.keys())))))

    if request.method == 'DELETE':
        # Delete data file
        delete_session(request.user.id, id)
        return json_response()
