"""
Afterglow Access Server: access to the various imaging surveys via SkyView
(skyview.gsfc.nasa.gov)
"""

from __future__ import absolute_import, division, print_function

from astropy import units as u
from astropy.coordinates import Angle
from astroquery.skyview import SkyView
from flask import Response, request

from skylib.io.conversion import get_image

from .. import app, errors, json_response, url_prefix
from ..auth import auth_required


__all__ = ['default_size', 'survey_scales']


class UnknownSurveyError(errors.AfterglowError):
    """
    SkyView does not host the given survey

    Extra attributes::
        survey: survey name
    """
    code = 404
    subcode = 3100
    message = 'SkyView does not host the given survey'


class SkyViewQueryError(errors.AfterglowError):
    """
    An error occurred during SkyView server query

    Extra attributes::
        msg: query error message
    """
    code = 502
    subcode = 3101
    message = 'SkyView query error'


class NoSurveyDataError(errors.AfterglowError):
    """
    Survey does not have any data for the given coordinates

    Extra attributes::
        survey: survey name
        position: coordinates or object name
    """
    code = 404
    subcode = 3102
    message = 'No data at the given coordinates'


# Default pixel scale for each known survey (arcsec/pixel); needed to return
# an image of the given angular size without resampling, i.e. with pixel
# dimensions depending on the FOV
survey_scales = {
    '0035MHz': 360.0, '0408MHz': 1265.625, '1420MHz (Bonn)': 900.0,
    '2MASS-H': 1.0, '2MASS-J': 1.0, '2MASS-K': 1.0,
    'AKARI N160': 15.0, 'AKARI N60': 15.0, 'AKARI WIDE-L': 15.0,
    'AKARI WIDE-S': 15.0,
    'BAT SNR 100-150': 300.0, 'BAT SNR 14-195': 300.0, 'BAT SNR 14-20': 300.0,
    'BAT SNR 150-195': 300.0, 'BAT SNR 20-24': 300.0, 'BAT SNR 24-35': 300.0,
    'BAT SNR 35-50': 300.0, 'BAT SNR 50-75': 300.0, 'BAT SNR 75-100': 300.0,
    'CDFS: LESS': 6.07412889,
    'CFHTLS-D-g': 0.10062, 'CFHTLS-D-i': 0.10062, 'CFHTLS-D-r': 0.10062,
    'CFHTLS-D-u': 0.10062, 'CFHTLS-D-z': 0.10062, 'CFHTLS-W-g': 0.201276,
    'CFHTLS-W-i': 0.201276, 'CFHTLS-W-r': 0.201276, 'CFHTLS-W-u': 0.201276,
    'CFHTLS-W-z': 0.201276,
    'CO': 450.0,
    'COBE DIRBE/AAM': 1265.6268, 'COBE DIRBE/ZSMA': 1265.6268,
    'COMPTEL': 3600.0,
    'DSS': 1.7, 'DSS1 Blue': 1.7, 'DSS1 Red': 1.7, 'DSS2 Blue': 1.0,
    'DSS2 IR': 1.0, 'DSS2 Red': 1.0,
    'EBHIS': 195.3828,
    'EGRET (3D)': 1800.0, 'EGRET <100 MeV': 1800.0, 'EGRET >100 MeV': 1800.0,
    'EUVE 171 A': 90.0, 'EUVE 405 A': 90.0, 'EUVE 555 A': 90.0,
    'EUVE 83 A': 90.0,
    'Fermi 1': 360.0, 'Fermi 2': 360.0, 'Fermi 3': 360.0, 'Fermi 4': 360.0,
    'Fermi 5': 360.0,
    'GALEX Far UV': 1.5, 'GALEX Near UV': 1.5,
    'GB6 (4850MHz)': 40.0,
    'GLEAM 103-134 MHz': 44.0, 'GLEAM 139-170 MHz': 34.0,
    'GLEAM 170-231 MHz': 28.0, 'GLEAM 72-103 MHz': 56.0,
    'GOODS: Chandra ACIS FB': 0.492, 'GOODS: Chandra ACIS HB': 0.492,
    'GOODS: Chandra ACIS SB': 0.492,
    'GOODS: HST ACS B': 0.03, 'GOODS: HST ACS I': 0.03,
    'GOODS: HST ACS V': 0.03, 'GOODS: HST ACS Z': 0.03,
    'GOODS: HST NICMOS': 0.1,
    'GOODS: Herschel 100': 1.2, 'GOODS: Herschel 160': 2.4,
    'GOODS: Herschel 250': 3.6, 'GOODS: Herschel 350': 4.8,
    'GOODS: Herschel 500': 7.2,
    'GOODS: Spitzer IRAC 3.6': 0.6, 'GOODS: Spitzer IRAC 4.5': 0.6,
    'GOODS: Spitzer IRAC 5.8': 0.6, 'GOODS: Spitzer IRAC 8.0': 0.6,
    'GOODS: Spitzer MIPS 24': 1.2,
    'GOODS: VLA North': 0.5,
    'GOODS: VLT ISAAC H': 0.15, 'GOODS: VLT ISAAC J': 0.15,
    'GOODS: VLT ISAAC Ks': 0.15, 'GOODS: VLT VIMOS R': 0.205,
    'GOODS: VLT VIMOS U': 0.205,
    'GRANAT/SIGMA': 194.8674456,
    'H-Alpha Comp': 150.0,
    'HEAO 1 A-2': 900.0,
    'HI4PI': 90.0,
    'HRI': 5.04,
    'HUDF: VLT ISAAC Ks': 0.15,
    'Hawaii HDF B': 0.3, 'Hawaii HDF HK': 0.3, 'Hawaii HDF I': 0.3,
    'Hawaii HDF R': 0.3, 'Hawaii HDF U': 0.3, 'Hawaii HDF V0201': 0.3,
    'Hawaii HDF V0401': 0.3, 'Hawaii HDF z': 0.3,
    'INT GAL 17-35 Flux': 240.40488, 'INT GAL 17-60 Flux': 240.40488,
    'INT GAL 35-80 Flux': 240.40488,
    'INTEGRAL/SPI GC': 360.0,
    'IRAS  12 micron': 90.0, 'IRAS  25 micron': 90.0, 'IRAS  60 micron': 90.0,
    'IRAS 100 micron': 90.0, 'IRIS  12': 90.0, 'IRIS  25': 90.0,
    'IRIS  60': 90.0, 'IRIS 100': 90.0,
    'Mellinger Blue': 36.0, 'Mellinger Green': 36.0, 'Mellinger Red': 36.0,
    'NEAT': 1.44,
    'NVSS': 15.000372,
    'PSPC 0.6 Deg-Int': 15.0, 'PSPC 1.0 Deg-Int': 15.0,
    'PSPC 2.0 Deg-Int': 15.0,
    'Planck 030': 108.0, 'Planck 044': 108.0, 'Planck 070': 108.0,
    'Planck 100': 108.0, 'Planck 143': 108.0, 'Planck 217': 108.0,
    'Planck 353': 108.0, 'Planck 545': 108.0, 'Planck 857': 108.0,
    'RASS Background 1': 720.0, 'RASS Background 2': 720.0,
    'RASS Background 3': 720.0, 'RASS Background 4': 720.0,
    'RASS Background 5': 720.0, 'RASS Background 6': 720.0,
    'RASS Background 7': 720.0,
    'RASS-Cnt Broad': 45.0, 'RASS-Cnt Hard': 45.0, 'RASS-Cnt Soft': 45.0,
    'ROSAT WFC F1': 60.0, 'ROSAT WFC F2': 60.0,
    'RXTE Allsky 3-20keV Flux': 1800.0, 'RXTE Allsky 3-8keV Flux': 1800.0,
    'RXTE Allsky 8-20keV Flux': 1800.0,
    'SDSSdr7g': 0.396, 'SDSSdr7i': 0.396, 'SDSSdr7r': 0.396, 'SDSSdr7u': 0.396,
    'SDSSdr7z': 0.396, 'SDSSg': 0.396, 'SDSSi': 0.396, 'SDSSr': 0.396,
    'SDSSu': 0.396, 'SDSSz': 0.396,
    'SFD Dust Map': 142.4328444,
    'SFD100m': 142.4328444,
    'SHASSA C': 47.39976, 'SHASSA CC': 47.39976, 'SHASSA H': 47.39976,
    'SHASSA Sm': 47.39976,
    'SUMSS 843 MHz': 12.6,
    'Stripe82VLA': 0.6,
    'SwiftXRTCnt': 3.6, 'SwiftXRTExp': 3.6, 'SwiftXRTInt': 3.6,
    'TGSS ADR1': 6.2,
    'UKIDSS-H': 0.40104, 'UKIDSS-J': 0.40104, 'UKIDSS-K': 0.40104,
    'UKIDSS-Y': 0.40104,
    'UVOT B Intensity': 1.0, 'UVOT U Intensity': 1.0,
    'UVOT UVM2 Intensity': 1.0, 'UVOT UVW1 Intensity': 1.0,
    'UVOT UVW2 Intensity': 1.0, 'UVOT V Intensity': 1.0,
    'UVOT WHITE Intensity': 1.0,
    'UltraVista-H': 1.0, 'UltraVista-J': 1.0, 'UltraVista-Ks': 1.0,
    'UltraVista-NB118': 1.0, 'UltraVista-Y': 1.0,
    'VLA FIRST (1.4 GHz)': 1.8,
    'VLSSr': 20.0,
    'WENSS': 21.093732,
    'WISE 12': 1.37484, 'WISE 22': 1.37484, 'WISE 3.4': 1.37484,
    'WISE 4.6': 1.37484,
    'WMAP ILC': 632.52, 'WMAP K': 632.52, 'WMAP Ka': 632.52, 'WMAP Q': 632.52,
    'WMAP V': 632.52, 'WMAP W': 632.52,
    'nH': 2430.0,
}

default_size = 1024

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

    - size: either rectangular image size in arcmins or comma-separated with
      and height in arcminutes
    - fmt: format of the data returned; default: "raw" - array of raw 32-bit
      floating-point pixel values, same as /data-files/[id]/pixels; otherwise,
      should be a format name (case-insensitive) of a particular image format
      supported by PIL/Pillow or matplotlib (if non-grayscale colormap), e.g.
      "jpeg" or "png"

    Other arguments define the visualization parameters for fmt="raw"; see
    :func:`skylib.io.conversion.get_image`.

    :param str name: survey name

    :return: JSON response containing the list of serialized catalog objects
        when no name supplied or a single catalog otherwise
    :rtype: flask.Response
    """
    if name is None:
        # List all surveys
        return json_response(SkyView.survey_dict)

    # Query specific survey: get RA/Dec FOV size
    # noinspection PyProtectedMember
    if name not in SkyView._valid_surveys:
        raise UnknownSurveyError(survey=name)
    args = request.args.to_dict()
    size = args.pop('size', None)
    if not size:
        raise errors.MissingFieldError('size')
    try:
        fov_ra = fov_dec = float(size)
    except ValueError:
        try:
            fov_ra, fov_dec = size.split(',')
            fov_ra, fov_dec = float(fov_ra), float(fov_dec)
        except ValueError:
            raise errors.ValidationError(
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
            raise errors.MissingFieldError('object|ra_hours,dec_degs')
        try:
            ra = float(ra)
            if not 0 <= ra < 24:
                raise ValueError()
        except ValueError:
            raise errors.ValidationError(
                'ra_hours', 'Expected 0 <= ra_hours < 24')
        dec = args.pop('dec_degs', None)
        if dec is None:
            raise errors.MissingFieldError('object|ra_hours,dec_degs')
        try:
            dec = float(dec)
            if not -90 <= ra <= 90:
                raise ValueError()
        except ValueError:
            raise errors.ValidationError(
                'dec_degs', 'Expected -90 <= dec_degs <= +90')
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
    data = res[0][0].data

    # Return image data in the requested format
    fmt = args.pop('fmt', 'raw').lower()
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
        raise errors.NotAcceptedError(accepted_mimetypes=accepted_mimetypes)

    # Otherwise, convert to the given raster format via SkyLib; the rest of
    # request args are interpreted as conversion arguments
    for s in ('data', 'fmt'):
        args.pop(s, None)
    return Response(get_image(data, fmt.upper(), **args), 200, None,
                    'image/{}'.format(fmt))
