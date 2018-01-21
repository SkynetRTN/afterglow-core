"""
Afterglow Access Server: source extraction
"""

from __future__ import absolute_import, division, print_function
from numpy import log10, pi
from astropy.wcs import WCS
from flask import request
from skylib.extraction import extract_sources
from skylib.photometry.aperture import aperture_photometry
from .. import Float, Resource, app, errors, json_response, url_prefix
from ..auth import auth_required
from .data_files import (
    UnknownDataFileError, get_exp_length, get_gain, get_data_file, get_phot_cal,
    get_subframe)


__all__ = []


class Source(Resource):
    """
    JSON-serializable extracted image data file source class

    Attributes::
        x: X coordinate of centroid
        y: Y coordinate of centroid
        a: semi-major axis in pixels
        b: semi-minor axis in pixels
        theta: major axis angle with respect to X in degrees, counter-clockwise
        x_err: estimated 1-sigma error of x
        y_err: estimated 1-sigma error of y
        ra_hours: right ascension of source in hours (available if astrometric
            calibration data are present in the data file header)
        dec_degs: declination of source in degrees (available if astrometric
            calibration data are present in the data file header)
        ra_err_arcsec: estimated 1-sigma error of ra_hours in arcseconds
        dec_err_arcsec: estimated 1-sigma error of dec_degs in arcseconds
        mag: source magnitude
        mag_err: estimated 1-sigma error of source magnitude
    """
    x = Float(default=None)
    y = Float(default=None)
    a = Float(default=None)
    b = Float(default=None)
    theta = Float(default=None)
    x_err = Float(default=None)
    y_err = Float(default=None)
    ra_hours = Float(default=None)
    dec_degs = Float(default=None)
    ra_err_arcsec = Float(default=None)
    dec_err_arcsec = Float(default=None)
    mag = Float(default=None)
    mag_err = Float(default=None)

    def __init__(self, s, x0, y0, texp, background_rms, m0=None, wcs=None):
        """
        Create image data file source class instance from a source table row

        :param `astropy.table.row.Row` s: source table row
        :param int x0: X offset to convert from source table coordinates to
            global image coordinates
        :param int y0: Y offset to convert from source table coordinates to
            global image coordinates
        :param float texp: exposure time in seconds
        :param array_like background_rms: background RMS map resulting from
            source extraction
        :param float m0: photometric zero point; if present, apply photometric
            calibration
        :param astropy.wcs.WCS wcs: optional WCS structure; if present, compute
            RA/Dec
        """
        super(Resource, self).__init__()

        x, y = s['x'], s['y']
        self.x, self.y = x + x0, y + y0

        try:
            self.a = s['a']
        except (KeyError, ValueError):
            pass

        try:
            self.b = s['b']
        except (KeyError, ValueError):
            pass

        try:
            self.theta = s['theta']*180/pi
        except (KeyError, ValueError):
            pass

        try:
            self.mag = s['mag']
        except (KeyError, ValueError):
            # Photometry was not requested; calculate magnitude from flux
            try:
                flux = s['flux']
            except (KeyError, ValueError):
                flux = 0
            if flux > 0:
                self.mag = -2.5*log10(flux/texp)

        if self.mag is not None:
            try:
                self.mag_err = s['mag_err']
            except (KeyError, ValueError):
                # Photometry was not requested; calculate mag error as inverse
                # SNR
                try:
                    flux = s['flux']
                except (KeyError, ValueError):
                    if self.mag is not None:
                        flux = 10**(-self.mag/2.5)*texp
                    else:
                        flux = 0
                if flux > 0:
                    self.mag_err = background_rms[
                        min(max(int(y + 0.5), 0), background_rms.shape[0] - 1),
                        min(max(int(x + 0.5), 0), background_rms.shape[1] - 1)
                    ]/flux

            # Apply photometric calibration
            if m0:
                self.mag += m0

        if wcs:
            # Apply astrometric calibration
            self.ra_hours, self.dec_degs = wcs.all_pix2world(self.x, self.y, 1)
            self.ra_hours /= 15


@app.route(url_prefix + 'data-files/<int:id>/sources')
@auth_required('user')
def data_file_sources(id):
    """
    Extract sources from the given image data file

    GET /data-files/[id]/sources?param=value...
        - return a list of image data file sources

    :param int id: data file ID

    Optional request parameters (general)::
        x: 1-based X position of top left corner of extraction region;
            default: 1
        y: 1-based Y position of top left corner of extraction region;
            default: 1
        width: width of extraction region; default: image width
        height: height of extraction region; default: image height

    Optional extraction parameters::
        threshold: detection threshold in units of background RMS; default: 2.5
        bk_size: box size for non-uniform background estimation; ignored if
            bkg_method=const; default: 1/64
        bk_filter_size: window size of a 2D median filter to apply to the
            low-res background map; (ny, nx) or a single integer for ny = nx;
            default: 3
        fwhm: estimated source FWHM in pixels; set to 0 or empty string to
            disable Gaussian pre-filtering of detection image; default: 2
        ratio: minor to major Gaussian kernel axis ratio, 0 < ratio <=
            1; ignored if fwhm=0; ratio=1 (default) means circular kernel;
            if ratio<1, it is assumed that fwhm corresponds to the minor axis
            of the kernel, which makes sense for sources elongated due to bad
            tracking; ignored if method=iraf since starfind supports only
            isotropic Gaussian filtering
        theta: position angle of the Gaussian kernel major axis with respect to
            the positive X axis, in degrees CCW; ignored if fwhm=0, ratio=1, or
            method=iraf: default: 0
        min_pixels: discard objects with less pixels above threshold; default: 3
        deblend: deblend overlapping sources (1); default: 0
        deblend_levels: number of multi-thresholding levels to use; ignored if
            deblend=0; default: 32
        deblend_contrast: fraction of the total flux to consider a component as
            a separate object; ignored if deblend=0; default: 0.005
        gain: electrons to data units conversion factor; default: taken from
            image file header; if unspecified and missing from the image header,
            mag_err is not calculated

    Optional photometry parameters::
        photometry::
            none (default): don't perform automatic photometry after source
                extraction; magnitudes are isophotal
            fixed: do fixed-aperture photometry; aperture parameters for all
                sources are defined by phot_a, phot_b, phot_theta, phot_a_in,
                phot_a_out, phot_b_out, and phot_theta_out
            auto: do automatic aperture photometry; individual aperture size
                for each source is derived from Kron radius multiplied by
                phot_k, phot_k_in, phot_k_out
        phot_a: aperture radius or semi-major axis (for elliptical aperture)
            in pixels
        phot_b: semi-minor aperture axis in pixels for elliptical aperture;
            if omitted or equal to phot_a, circular aperture is used
        phot_theta: rotation angle of semi-major axis in degrees
            counter-clockwise from the X axis; default: 0; unused for circular
            aperture
        phot_a_in: inner radius or semi-major axis of annulus in pixels;
            defaults to phot_a (annulus starts right at the aperture boundary)
        phot_a_out: outer radius or semi-major axis of annulus in pixels;
            setting phot_a_out enables local background subtraction and
            calculation of photometry errors; must be > phot_a_in (or phot_a,
            if phot_a_in is unspecified)
        phot_b_out: annulus outer semi-minor axis; defaults
            to phot_a_out*phot_b/phot_a, i.e. assumes the same ellipticity
            as the aperture
        phot_theta_out: rotation angle of the outer semi-major annulus axis
            in degrees counter-clockwise from the X axis; defaults
            to phot_theta, i.e. same rotation as the aperture
        phot_k: for photometry=auto, this is the Kron radius scaling factor
            used to compute the aperture radius: phot_a = a/b*r*phot_k, phot_b =
            b/a*r*phot_k, where a,b are semi-major and semi-minor axes of the
            source's isophotal profile, and r is Kron radius; default: 2.5
        phot_k_in: inner annulus radius scaling factor: phot_a_in =
            a/b*r*phot_k_in, phot_b_in = b/a*r*phot_k_in; default: 1.5*phot_k
        phot_k_out: outer annulus radius scaling factor: phot_a_out =
            a/b*r*phot_k_out, phot_b_out = b/a*r*phot_k_out; must be greater
            than phot_k_in; default: 2*phot_k

    :return: JSON response containing the list of serialized image data file
        source objects
    :rtype: `flask.Response`
    """
    # Extract background estimation and source extraction keywords
    try:
        x0 = int(request.args.get('x', 1))
    except ValueError:
        raise errors.ValidationError('x', 'x must be integer')
    try:
        y0 = int(request.args.get('y', 1))
    except ValueError:
        raise errors.ValidationError('y', 'y must be integer')
    args = {name: val for name, val in request.args.to_dict().items()
            if name not in ('x', 'y', 'width', 'height')}
    bkg_kw = {}
    for name in ('size', 'filter_size'):
        try:
            bkg_kw[name] = args.pop('bk_' + name)
        except KeyError:
            pass

    # Get photometry parameters
    photometry = args.pop('photometry', 'none')
    try:
        a = float(args.pop('phot_a'))
        if a <= 0:
            raise errors.ValidationError(
                'phot_a', 'phot_a must be positive', 422)
    except ValueError:
        raise errors.ValidationError('phot_a', 'A float expected')
    except KeyError:
        if photometry == 'fixed':
            raise errors.MissingFieldError('phot_a')
        a = None

    try:
        b = float(args.pop('phot_b'))
        if b <= 0:
            raise errors.ValidationError(
                'phot_b', 'phot_b must be positive', 422)
        if a is not None and b > a:
            raise errors.ValidationError(
                'phot_b', 'phot_b must be less than or equal to phot_a', 422)
    except ValueError:
        raise errors.ValidationError('phot_b', 'A float expected')
    except KeyError:
        b = None

    try:
        theta = float(args.pop('phot_theta'))
    except ValueError:
        raise errors.ValidationError('phot_theta', 'A float expected')
    except KeyError:
        theta = 0

    try:
        a_in = float(args.pop('phot_a_in'))
        if a_in <= 0:
            raise errors.ValidationError(
                'phot_a_in', 'phot_a_in must be positive', 422)
    except ValueError:
        raise errors.ValidationError('phot_a_in', 'A float expected')
    except KeyError:
        a_in = None

    try:
        a_out = float(args.pop('phot_a_out'))
        if a_out <= 0:
            raise errors.ValidationError(
                'phot_a_out', 'phot_a_out must be positive', 422)
        if a_in is not None and a_out <= a_in:
            raise errors.ValidationError(
                'phot_a_out', 'phot_a_out must be greater than phot_a_in', 422)
    except ValueError:
        raise errors.ValidationError('phot_a_out', 'A float expected')
    except KeyError:
        a_out = None

    try:
        b_out = float(args.pop('phot_b_out'))
        if b_out <= 0:
            raise errors.ValidationError(
                'phot_b_out', 'phot_b_out must be positive', 422)
        if a_out is not None and b_out > a_out:
            raise errors.ValidationError(
                'phot_b_out',
                'phot_b_out must be less than or equal to phot_a_out', 422)
    except ValueError:
        raise errors.ValidationError('phot_b_out', 'A float expected')
    except KeyError:
        b_out = None

    try:
        theta_out = float(args.pop('phot_theta_out'))
    except ValueError:
        raise errors.ValidationError('phot_theta_out', 'A float expected')
    except KeyError:
        theta_out = None

    try:
        k = float(args.pop('phot_k'))
        if k <= 0:
            raise errors.ValidationError(
                'phot_k', 'phot_k must be positive', 422)
    except ValueError:
        raise errors.ValidationError('phot_k', 'A float expected')
    except KeyError:
        k = 2.5

    try:
        k_in = float(args.pop('phot_k_in'))
        if k_in <= 0:
            raise errors.ValidationError(
                'phot_k_in', 'phot_k_in must be positive', 422)
    except ValueError:
        raise errors.ValidationError('phot_k_in', 'A float expected')
    except KeyError:
        k_in = 1.5*k

    try:
        k_out = float(args.pop('phot_k_out'))
        if k_out < 0:
            raise errors.ValidationError(
                'phot_k_out', 'phot_k_out must be positive', 422)
        if k_out and k_out <= k_in:
            raise errors.ValidationError(
                'phot_k_out', 'phot_k_out must be greater than phot_k_in', 422)
    except ValueError:
        raise errors.ValidationError('phot_k_out', 'A float expected')
    except KeyError:
        k_out = 2*k

    # Get image data
    try:
        pixels = get_subframe(id)
    except errors.AfterglowError:
        raise
    except Exception:
        raise UnknownDataFileError(id=id)

    hdr = get_data_file(id)[0].header

    # Get exposure time, gain, and photometric calibration
    texp = get_exp_length(hdr)
    if 'gain' not in args:
        gain = get_gain(hdr)
        if gain:
            args['gain'] = float(hdr)
    else:
        gain = args['gain']
    phot_cal = get_phot_cal(hdr)

    # Extract sources
    source_table, background, background_rms = extract_sources(
        pixels, bkg_kw=bkg_kw, **args)

    if photometry != 'none':
        # Do automatic aperture photometry
        if photometry == 'fixed':
            phot_kwargs = dict(
                a=a, b=b, theta=theta, a_in=a_in, a_out=a_out, b_out=b_out,
                theta_out=theta_out)
        else:
            phot_kwargs = dict(k=k, k_in=k_in, k_out=k_out)
        source_table = aperture_photometry(
            pixels, source_table, background, background_rms, texp, gain,
            **phot_kwargs)

    # If present, apply photometric calibration to instrumental magnitudes
    try:
        m0 = phot_cal['m0']
    except KeyError:
        m0 = 0

    # Apply astrometric calibration if present
    # noinspection PyBroadException
    try:
        wcs = WCS(hdr)
        if not wcs.has_celestial:
            wcs = None
    except Exception:
        wcs = None

    return json_response([Source(s, x0, y0, texp, background_rms, m0, wcs)
                          for s in source_table])
