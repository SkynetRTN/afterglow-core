"""
Afterglow Core: API v1 imaging survey views
"""

import sys

from astropy import units as u
from astropy.coordinates import Angle
from astroquery.skyview import SkyView
from flask import Response, request
from io import BytesIO

from skylib.io.conversion import get_image

from .... import app, json_response
from ....auth import auth_required
from ....resources.imaging_surveys import survey_scales, default_size
from ....errors import MissingFieldError, NotAcceptedError, ValidationError
from ....errors.imaging_survey import (
    UnknownSurveyError, SkyViewQueryError, NoSurveyDataError)
from . import url_prefix


resource_prefix = url_prefix + 'imaging-surveys/'


@app.route(resource_prefix[:-1])
@app.route(resource_prefix + '<name>')
@auth_required('user')
def get_imaging_surveys(name=None):
    """
    Return available image surveys or query SkyView for specific survey

    GET /imaging-surveys
        - return a list of all available survey names

    GET /imaging-surveys/[name]?ra_hours=...&dec_degs=...&size=...&fmt=...&args
        - return image centered at the given equatorial coordinates

    GET /imaging-surveys/[name]?object=...&size=...&fmt=...&args
        - return image centered at the given object; name is resolved by SIMBAD
          and NED

    - size: either rectangular image size in arcmins or comma-separated width
      and height in arcminutes
    - fmt: format of the data returned; default: "raw" - array of raw 32-bit
      floating-point pixel values, same as /data-files/[id]/pixels; "fits" -
      original FITS file as returned by SkyView; otherwise, `fmt`should be
      a format name (case-insensitive) of a particular image format supported
      by PIL/Pillow or matplotlib (if non-grayscale colormap), e.g. "jpeg" or
      "png"

    Other arguments define the visualization parameters for formats other than
    raw and fits; see :func:`skylib.io.conversion.get_image`.

    :param str name: survey name

    :return: binary or JSON response, depending on `fmt`, containing the image
        retrieved from the given survey
    :rtype: flask.Response
    """
    if name is None:
        # List all surveys
        return json_response(dict(items=list(SkyView.survey_dict.keys())))

    # Query specific survey: get RA/Dec FOV size
    # noinspection PyProtectedMember
    if name not in SkyView._valid_surveys:
        raise UnknownSurveyError(survey=name)
    args = request.args.to_dict()
    size = args.pop('size', None)
    if not size:
        raise MissingFieldError('size')
    try:
        fov_ra = fov_dec = float(size)
    except ValueError:
        try:
            fov_ra, fov_dec = size.split(',')
            fov_ra, fov_dec = float(fov_ra), float(fov_dec)
        except ValueError:
            raise ValidationError(
                'size', 'Expected FOV size or RA,Dec size in arcmins')
    try:
        scale = survey_scales[name]
    except KeyError:
        # Unknown scale: query region of the given size resampling to 1K image
        if fov_ra > fov_dec:
            w, h = int(default_size*fov_ra/fov_dec + 0.5), default_size
        else:
            w, h = default_size, int(default_size*fov_dec/fov_ra + 0.5)
        # noinspection PyUnresolvedReferences
        kwargs = {
            'pixels': '{},{}'.format(w, h), 'sampler': 'Spline5',
            'width': fov_ra*u.arcmin, 'height': fov_dec*u.arcmin}
    else:
        # Assuming default scale for the survey, set the number of pixels from
        # pixel scale
        kwargs = {'pixels': '{},{}'.format(
            int(fov_ra*60/scale + 0.5), int(fov_dec*60/scale + 0.5))}

    # Get object name or coordinates
    position = args.pop('object', None)
    if not position:
        ra = args.pop('ra_hours', None)
        if ra is None:
            raise MissingFieldError('object|ra_hours,dec_degs')
        try:
            ra = float(ra)
            if not 0 <= ra < 24:
                raise ValueError()
        except ValueError:
            raise ValidationError('ra_hours', 'Expected 0 <= ra_hours < 24')
        dec = args.pop('dec_degs', None)
        if dec is None:
            raise MissingFieldError('object|ra_hours,dec_degs')
        try:
            dec = float(dec)
            if not -90 <= ra <= 90:
                raise ValueError()
        except ValueError:
            raise ValidationError('dec_degs', 'Expected -90 <= dec_degs <= +90')
        # noinspection PyUnresolvedReferences
        position = '{}, {}'.format(
            Angle(ra*u.hour).to_string(sep=' ', precision=3, pad=2),
            Angle(dec*u.deg).to_string(sep=' ', precision=2, alwayssign=True,
                                       pad=2))

    # Query SkyView; a single FITS expected on output
    try:
        res = SkyView.get_images(
            position, name, cache=False, show_progress=False, **kwargs)
    except Exception as e:
        raise SkyViewQueryError(msg=str(e))

    if not res:
        raise NoSurveyDataError(survey=name, position=position)

    # Return image data in the requested format
    fmt = args.pop('fmt', 'raw').lower()
    if fmt == 'fits':
        buf = BytesIO()
        res[0].writeto(buf, output_verify='silentfix')
        return Response(buf.getvalue(), 200, None, 'image/fits')

    data = res[0][0].data

    if fmt == 'raw':
        # Return as array of pixels
        accepted_mimetypes = request.headers['Accept']
        if accepted_mimetypes:
            allow_json = allow_bin = False
            for mt in accepted_mimetypes.split(','):
                mtype, subtype = mt.split(';')[0].strip().lower().split('/')
                if mtype in ('application', '*'):
                    if subtype == 'json':
                        allow_json = True
                    elif subtype == 'octet-stream':
                        allow_bin = True
                    elif subtype == '*':
                        allow_json = allow_bin = True
        else:
            # Accept header not specified, assume all types are allowed
            allow_json = allow_bin = True

        if allow_bin:
            # Make sure data are in little-endian byte order before sending over
            # the net
            if data.dtype.byteorder == '>' or \
                    data.dtype.byteorder == '=' and sys.byteorder == 'big':
                data = data.byteswap()
            data = data.tobytes()
            mimetype = 'application/octet-stream'
            return Response(data, 200, None, mimetype)

        if allow_json:
            return json_response(data.tolist(), 200)

        # Could not send data in any of the formats supported by the client
        raise NotAcceptedError(accepted_mimetypes=accepted_mimetypes)

    # Otherwise, convert to the given raster format via SkyLib; the rest of
    # request args are interpreted as conversion arguments
    for s in ('data', 'fmt'):
        args.pop(s, None)
    return Response(get_image(data, fmt.upper(), **args), 200, None,
                    'image/{}'.format(fmt))
