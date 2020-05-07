"""
Afterglow Core: photometry data structures
"""

from marshmallow.fields import String

from . import AfterglowSchema, Float, Resource
from .source_extraction import SourceExtractionData


class Mag(AfterglowSchema):
    value = Float()
    error = Float()


class IPhotometry(AfterglowSchema):
    flux = Float()  # type: float
    flux_error = Float()  # type: float
    mag = Float()  # type: float
    mag_error = Float()  # type: float


class IAperture(AfterglowSchema):
    aper_a = Float()  # type: float
    aper_b = Float()  # type: float
    aper_theta = Float()  # type: float
    annulus_a_in = Float()  # type: float
    annulus_b_in = Float()  # type: float
    annulus_theta_in = Float()  # type: float
    annulus_a_out = Float()  # type: float
    annulus_b_out = Float()  # type: float
    annulus_theta_out = Float()  # type: float


class PhotSettings(AfterglowSchema):
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


class PhotometryData(SourceExtractionData, IPhotometry):
    """
    Description of object returned by batch photometry
    """
    @classmethod
    def from_phot_table(cls, row, source, **kwargs):
        """
        Create photometry data class instance from a source extraction object
        and a photometry table row

        :param numpy.void row: photometry table row
        :param SourceExtractionData source: input source object
        :param kwargs: see :meth:`from_source_table`
        """
        data = cls(source, **kwargs)

        data.x = row['x']
        data.y = row['y']
        data.flux = row['flux']
        data.flux_error = row['flux_err']
        data.mag = row['mag']
        data.mag_error = row['mag_err']

        if row['aper_a']:
            data.aper_a = row['aper_a']
            data.aper_b = row['aper_b']
            data.aper_theta = row['aper_theta']
            data.annulus_a_in = row['aper_a_in']
            data.annulus_b_in = \
                row['aper_a_in']*row['aper_b_out']/row['aper_a_out']
            data.annulus_theta_in = data.annulus_theta_out = \
                row['aper_theta_out']
            data.annulus_a_out = row['aper_a_out']
            data.annulus_b_out = row['aper_b_out']

        return data


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


__all__ = [name for name, value in globals().items()
           if issubclass(value, AfterglowSchema)]
