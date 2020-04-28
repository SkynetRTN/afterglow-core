"""
Afterglow Access Server: image data file photometry
"""

from __future__ import absolute_import, division, print_function
from flask import request
from numpy import array, sqrt
from astropy.wcs import WCS

from skylib.photometry.aperture import aperture_photometry
from skylib.extraction.centroiding import centroid_iraf

from .. import Float, Resource, app, auth, errors, json_response, url_prefix
from .data_files import (
    MissingWCSError, get_exp_length, get_gain, get_data_file, get_phot_cal)


__all__ = ['Photometry', 'get_photometry']


class Photometry(Resource):
    """
    JSON-serializable photometry results

    Attributes::
        flux: flux within the aperture in ADUs; mean background within the
            annulus is subtracted if annulus is enabled
        flux_err: estimated 1-sigma error of flux
        mag: magnitude computed as -2.5log10(flux/texp) + optional calibration
            terms if calibration data are available
        mag_err: estimated 1-sigma error of magnitude
        x, y: pixel coordinates of the aperture center
        a: aperture radius (or semi-major axis) in pixels
        b: semi-minor axis of the aperture
        theta: aperture position angle in degrees CCW if `a` != `b`
        a_in: inner annulus radius (or semi-major axis) in pixels; not set if
            local background subtraction was not used
        a_out: outer annulus radius (or semi-major axis) in pixels
        b_out: semi-minor outer axis of the annulus
        theta_out: annulus position angle in degrees CCW if `a` != `b`
        area: area within the aperture in square pixels
        background_area: annulus area in pixels if local background subtraction
            was enabled; not set otherwise
        background: mean background within the aperture estimated from the
            annulus if enabled; not set otherwise
        background_rms: RMS of background within the annulus if local background
            subtraction was enabled; not set otherwise

    """
    flux = Float()  # type: float
    flux_err = Float()  # type: float
    mag = Float()  # type: float
    mag_err = Float()  # type: float
    x = Float()  # type: float
    y = Float()  # type: float
    a = Float()  # type: float
    b = Float()  # type: float
    theta = Float()  # type: float
    a_in = Float()  # type: float
    a_out = Float()  # type: float
    b_out = Float()  # type: float
    theta_out = Float()  # type: float
    area = Float()  # type: float
    background_area = Float()  # type: float
    background = Float()  # type: float
    background_rms = Float()  # type: float


def get_photometry(data, texp, gain, phot_cal, x, y, a, b=None, theta=0,
                   a_in=None, a_out=None, b_out=None, theta_out=None,
                   background=None, background_rms=None, centroid_radius=None):
    """
    Photometer the given image

    :param array_like data: image data array
    :param float texp: exposure time in seconds
    :param float gain: CCD gain in e-/ADU
    :param phot_cal: optional photometric calibration as returned by
        :func:`afterglow_1_0.data_files.get_phot_cal`
    :param float x: X position of aperture center (1-based)
    :param float y: Y position of aperture center (1-based)
    :param float a: aperture radius or semi-major axis (for elliptical
        aperture), in pixels
    :param float b: semi-minor aperture axis in pixels for elliptical aperture;
        if omitted or equal to `a`, circular aperture is used
    :param float theta: rotation angle of semi-major axis in degrees
        counter-clockwise from the X axis; default: 0; unused for circular
        aperture
    :param float a_in: inner radius or semi-major axis of annulus in pixels;
        defaults to `a` (annulus starts right at the aperture boundary)
    :param float a_out: outer radius or semi-major axis of annulus in pixels;
        setting `a_out` enables local background subtraction; must be > a_in
        (or a, if a_in is unspecified)
    :param float b_out: outer semi-minor axis of annulus; defaults to a_out*b/a,
        i.e. assumes the same ellipticity as the aperture
    :param float theta_out: rotation angle of the outer semi-major annulus axis
        in degrees counter-clockwise from the X axis; defaults to `theta`, i.e.
        same rotation as the aperture
    :param array_like background: optional background level, either a scalar or
        a map, same shape as `data`; used to calculate photometry error when
        annulus is not used
    :param array_like background_rms: optional background RMS, either a scalar
        or a map, same shape as `data`; used to calculate photometry error when
        annulus is not used
    :param float | None centroid_radius: if set, then the input XY coordinates
        are treated as the initial guess, and the actual coordinates are
        calculated by finding the photocenter around (`x`, `y`) within the
        given radius in pixels

    :return: photometry result object
    :rtype: :class:_`Photometry`
    """
    if not texp:
        texp = 1
    if not gain:
        gain = 1
    if b is None:
        b = a
    if a_in is None:
        a_in = a
    if b_out is None:
        b_out = a_out
        if b_out is not None:
            b_out *= b/a
    if theta_out is None:
        theta_out = theta

    if centroid_radius:
        # Find centroid coordinates using the IRAF-like method
        x, y = centroid_iraf(data, x, y, centroid_radius)

    source = aperture_photometry(
        data,
        array([(x, y, 0, 0, 0)],
              dtype=[('x', float), ('y', float), ('flux', float),
                     ('saturated', int), ('flag', int)]),
        background, background_rms, texp, gain, a, b, theta, a_in, a_out, b_out,
        theta_out)[0]

    # Apply calibration if available
    if source['mag']:
        try:
            source['mag'] += phot_cal['m0']
        except (KeyError, TypeError):
            pass
    if source['mag_err']:
        try:
            source['mag_err'] = sqrt(source['mag_err']**2 +
                                     phot_cal['m0_err']**2)
        except (KeyError, TypeError):
            pass

    return Photometry(
        flux=source['flux'], flux_err=source['flux_err'],
        mag=source['mag'], mag_err=source['mag_err'],
        x=x, y=y,
        a=source['aper_a'], b=source['aper_b'], theta=source['aper_theta'],
        a_in=source['aper_a_in'], a_out=source['aper_a_out'],
        b_out=source['aper_b_out'], theta_out=source['aper_theta_out'],
        area=source['aper_area'],
        background_area=source['background_area'],
        background=source['background'],
        background_rms=source['background_rms'],
    )


@app.route(url_prefix + 'data-files/<int:id>/photometry')
@auth.auth_required('user')
def data_file_photometry(id):
    """
    Photometer the given aperture, with optional local background subtraction

    GET /data-files/[id]/photometry?param=value...
        - return Photometry object

    :param int id: data file ID

    Request parameters::
        x: X position or a comma-separated list of positions of aperture
            centers; the ending comma is ignored, so, if the caller wants a list
            even in the case of a single input item, the input value can be
            terminated with a comma
        y: Y position or a comma-separated list of positions of aperture
            centers; same length as `x`
        ra_hours: RA or a comma-separated list of RAs of aperture centers; can
            be passed instead of `x` and `y` provided the data file is
            astrometric-calibrated
        dec_degs: Dec or a comma-separated list of Decs of aperture centers; can
            be passed instead of `x` and `y` provided the data file is
            astrometric-calibrated
        a: aperture radius os semi-major axis (for elliptical aperture), in
            pixels
        b: semi-minor aperture axis in pixels for elliptical aperture; if
            omitted or equal to `a`, circular aperture is used
        theta: rotation angle of semi-major axis in degrees counter-clockwise
            from the X axis; default: 0; unused for circular aperture
        a_in: inner radius or semi-major axis of annulus in pixels; defaults to
            `a` (annulus starts right at the aperture boundary)
        a_out: outer radius or semi-major axis of annulus in pixels; setting
            `a_out` enables local background subtraction; must be > a_in (or a,
            if a_in is unspecified)
        b_out: outer semi-minor axis of annulus; defaults to a_out*b/a, i.e.
            assumes the same ellipticity as the aperture
        theta_out: rotation angle of the outer semi-major annulus axis in
            degrees counter-clockwise from the X axis; defaults to `theta`, i.e.
            same rotation as the aperture
        centroid_radius: if given, then the input XY coordinates are treated as
            the initial guess, and the actual coordinates are calculated by
            finding the photocenter around (`x`, `y`) within the given radius in
            pixels

    :return: JSON response containing serialized Photometry object (single xy
        or RA/Dec value) or a list of PHotometry objects otherwise
    :rtype: `flask.Response`
    """
    # Get request parameters
    try:
        x, y = request.args['x'], request.args['y']
    except KeyError:
        x = y = None
        try:
            ra, dec = request.args['ra_hours'], request.args['dec_degs']
        except KeyError:
            raise errors.MissingFieldError(field='x,y|ra_hours,dec_degs')
        else:
            # RA/Dec supplied
            multiple = ',' in ra
            if multiple:
                ra, dec = ra.split(','), dec.split(',')
                if not ra[-1].strip():
                    ra = ra[:-1]
                if not dec[-1].strip():
                    dec = dec[-1]
                if len(ra) != len(dec):
                    raise errors.ValidationError(
                        'dec_degs', 'Same number of items expected')
                try:
                    ra = [float(_ra) for _ra in ra]
                except ValueError:
                    raise errors.ValidationError(
                        'ra_hours', 'Floating-point value(s) expected')
                try:
                    dec = [float(_dec) for _dec in dec]
                except ValueError:
                    raise errors.ValidationError(
                        'dec_degs', 'Floating-point value(s) expected')
            else:
                try:
                    ra = [float(ra)]
                except ValueError:
                    raise errors.ValidationError(
                        'ra', 'Floating-point value(s) expected')
                try:
                    dec = [float(dec)]
                except ValueError:
                    raise errors.ValidationError(
                        'dec', 'Floating-point value(s) expected')
    else:
        # XY supplied
        ra = dec = None

        # A list of values?
        multiple = ',' in x
        if multiple:
            x, y = x.split(','), y.split(',')
            if not x[-1].strip():
                x = x[:-1]
            if not y[-1].strip():
                y = y[:-1]
            if len(x) != len(y):
                raise errors.ValidationError(
                    'y', 'Same number of items expected')
            try:
                x = [float(_x) for _x in x]
            except ValueError:
                raise errors.ValidationError(
                    'x', 'Floating-point value(s) expected')
            try:
                y = [float(_y) for _y in y]
            except ValueError:
                raise errors.ValidationError(
                    'y', 'Floating-point value(s) expected')
        else:
            try:
                x = [float(x)]
            except ValueError:
                raise errors.ValidationError(
                    'x', 'Floating-point value(s) expected')
            try:
                y = [float(y)]
            except ValueError:
                raise errors.ValidationError(
                    'y', 'Floating-point value(s) expected')

    try:
        a = float(request.args['a'])
        if a <= 0:
            raise errors.ValidationError(
                'a', 'Aperture radius/semi-major axis must be positive', 422)
    except KeyError:
        raise errors.MissingFieldError(field='a')
    except ValueError:
        raise errors.ValidationError('a', 'Floating-point value expected')

    try:
        b = float(request.args['b'])
        if b <= 0:
            raise errors.ValidationError(
                'b', 'Semi-minor aperture axis must be positive', 422)
    except KeyError:
        b = None
    except ValueError:
        raise errors.ValidationError('b', 'Floating-point value expected')

    try:
        theta = float(request.args['theta'])
    except KeyError:
        theta = None
    except ValueError:
        raise errors.ValidationError('theta', 'Floating-point value expected')

    try:
        a_in = float(request.args['a_in'])
        if a_in <= 0:
            raise errors.ValidationError(
                'a_in',
                'Inner annulus radius/semi-major axis must be positive', 422)
    except KeyError:
        a_in = None
    except ValueError:
        raise errors.ValidationError('a_in', 'Floating-point value expected')

    try:
        a_out = float(request.args['a_out'])
        if a_out <= 0:
            raise errors.ValidationError(
                'a_out',
                'Outer annulus radius/semi-major axis must be positive', 422)
    except KeyError:
        a_out = None
    except ValueError:
        raise errors.ValidationError('a_out', 'Floating-point value expected')

    try:
        b_out = float(request.args['b_out'])
        if b_out <= 0:
            raise errors.ValidationError(
                'b_out', 'Outer annulus semi-minor axis must be positive', 422)
    except KeyError:
        b_out = None
    except ValueError:
        raise errors.ValidationError('b_out', 'Floating-point value expected')

    try:
        theta_out = float(request.args['theta_out'])
    except KeyError:
        theta_out = None
    except ValueError:
        raise errors.ValidationError(
            'theta_out', 'Floating-point value expected')

    centroid_radius = request.args.get('centroid_radius')
    if centroid_radius:
        try:
            centroid_radius = float(centroid_radius)
            if not centroid_radius:
                centroid_radius = None
            elif centroid_radius < 0:
                raise ValueError()
        except ValueError:
            raise errors.ValidationError(
                'centroid_radius', 'Positive floating-point value expected')
    else:
        centroid_radius = None

    # Get image data
    data, hdr = get_data_file(auth.current_user.id, id)

    if ra is not None and dec is not None:
        # Convert RA/Dec to XY if we have astrometric calibration
        wcs = WCS(hdr)
        if not any(wcs.wcs.ctype):
            raise MissingWCSError()
        x, y = wcs.all_world2pix(array(ra)*15, array(dec), 1)

    res = [
        get_photometry(
            data, get_exp_length(hdr), get_gain(hdr), get_phot_cal(hdr), _x, _y,
            a, b, theta, a_in, a_out, b_out, theta_out,
            centroid_radius=centroid_radius)
        for _x, _y in zip(x, y)]

    if not multiple:
        res = res[0]
    return json_response(res)
