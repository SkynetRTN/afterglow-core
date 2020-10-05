"""
Afterglow Core: photometry-related schemas
"""

from marshmallow.fields import String

from .source_extraction import SourceExtractionDataSchema
from ... import AfterglowSchema, Float


__all__ = [
    'IApertureSchema', 'IPhotometrySchema', 'MagSchema', 'PhotometrySchema',
    'PhotometryDataSchema', 'PhotSettingsSchema',
]


class MagSchema(AfterglowSchema):
    value = Float()
    error = Float()


class IPhotometrySchema(AfterglowSchema):
    flux = Float()  # type: float
    flux_error = Float()  # type: float
    mag = Float()  # type: float
    mag_error = Float()  # type: float


class IApertureSchema(AfterglowSchema):
    aper_a = Float()  # type: float
    aper_b = Float()  # type: float
    aper_theta = Float()  # type: float
    annulus_a_in = Float()  # type: float
    annulus_b_in = Float()  # type: float
    annulus_theta_in = Float()  # type: float
    annulus_a_out = Float()  # type: float
    annulus_b_out = Float()  # type: float
    annulus_theta_out = Float()  # type: float


class PhotSettingsSchema(AfterglowSchema):
    mode = String(default='aperture')  # type: str
    a = Float(default=None)  # type: float
    b = Float(default=None)  # type: float
    theta = Float(default=0)  # type: float
    a_in = Float(default=None)  # type: float
    a_out = Float(default=None)  # type: float
    b_out = Float(default=None)  # type: float
    theta_out = Float(default=None)  # type: float
    gain = Float(default=None)  # type: float
    centroid_radius = Float(default=0)  # type: float
    zero_point = Float(default=0)  # type: float


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
