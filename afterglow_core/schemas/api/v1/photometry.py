"""
Afterglow Core: photometry-related schemas
"""

from typing import Optional

from marshmallow.fields import String

from ... import AfterglowSchema, Boolean, Float
from .source_extraction import SourceExtractionDataSchema


__all__ = [
    'IApertureSchema', 'IPhotometrySchema', 'MagSchema', 'PhotometrySchema',
    'PhotometryDataSchema', 'PhotSettingsSchema',
]


class MagSchema(AfterglowSchema):
    value = Float()
    error = Float()


class IPhotometrySchema(AfterglowSchema):
    flux: float = Float()
    flux_error: float = Float()
    mag: Optional[float] = Float()
    mag_error: Optional[float] = Float()


class IApertureSchema(AfterglowSchema):
    aper_a: float = Float()
    aper_b: float = Float()
    aper_theta: float = Float()
    annulus_a_in: float = Float()
    annulus_b_in: float = Float()
    annulus_theta_in: float = Float()
    annulus_a_out: float = Float()
    annulus_b_out: float = Float()
    annulus_theta_out: float = Float()


class PhotSettingsSchema(AfterglowSchema):
    mode: str = String(default='aperture')
    a: float = Float(default=None)
    b: float = Float(default=None)
    theta: float = Float(default=0)
    a_in: float = Float(default=None)
    a_out: float = Float(default=None)
    b_out: float = Float(default=None)
    theta_out: float = Float(default=None)
    gain: float = Float(default=None)
    centroid_radius: float = Float(default=0)
    zero_point: float = Float(default=0)
    fix_aper: bool = Boolean(default=True)
    fix_ell: bool = Boolean(default=True)
    fix_rot: bool = Boolean(default=True)
    apcorr_tol: float = Float(default=0.0001)


class PhotometryDataSchema(SourceExtractionDataSchema, IPhotometrySchema,
                           IApertureSchema):
    """
    Description of object returned by batch photometry
    """
    pass


class PhotometrySchema(AfterglowSchema):
    """
    JSON-serializable photometry results

    Attributes::
        flux: flux within the aperture in ADUs; mean background within the
            annulus is subtracted if annulus is enabled
        flux_err: estimated 1-sigma error of flux
        mag: magnitude computed as -2.5log10(flux/texp)
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
        background_rms: RMS of background within the annulus if local
            background subtraction was enabled; not set otherwise

    """
    flux: float = Float()
    flux_err: float = Float()
    mag: float = Float()
    mag_err: float = Float()
    x: float = Float()
    y: float = Float()
    a: float = Float()
    b: float = Float()
    theta: float = Float()
    a_in: float = Float()
    a_out: float = Float()
    b_out: float = Float()
    theta_out: float = Float()
    area: float = Float()
    background_area: float = Float()
    background: float = Float()
    background_rms: float = Float()
