"""
Afterglow Core: image data file photometry
"""

from __future__ import absolute_import, division, print_function
from numpy import array, sqrt

from skylib.photometry.aperture import aperture_photometry
from skylib.extraction.centroiding import centroid_iraf

from ..models.photometry import Photometry


__all__ = ['get_photometry']


def get_photometry(data, texp, gain, phot_cal, x, y, a, b=None, theta=0,
                   a_in=None, a_out=None, b_out=None, theta_out=None,
                   background=None, background_rms=None, centroid_radius=None):
    """
    Photometer the given image

    :param array_like data: image data array
    :param float texp: exposure time in seconds
    :param float gain: CCD gain in e-/ADU
    :param phot_cal: optional photometric calibration as returned by
        :func:`afterglow_core.data_files.get_phot_cal`
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
