"""
Afterglow Core: photometry data models
"""

from typing import Optional

from marshmallow.fields import Float, String
import numpy

from ..schemas import AfterglowSchema
from .source_extraction import SourceExtractionData


__all__ = [
    'IAperture', 'IPhotometry', 'Mag', 'Photometry', 'PhotometryData',
    'PhotSettings',
]


class Mag(AfterglowSchema):
    value = Float()  # type: float
    error = Float()  # type: float


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
    zero_point = Float(default=0)  # type: float


class PhotometryData(SourceExtractionData, IPhotometry, IAperture):
    """
    Description of object returned by batch photometry
    """
    def __init__(self, source: Optional[SourceExtractionData] = None,
                 row: Optional[numpy.void] = None,
                 zero_point: float = 0, **kwargs):
        """
        Create photometry data class instance from a source extraction object
        and a photometry table row

        :param source: input source object
        :param row: photometry table row
        :param zero_point: apply the optional zero point to instrumental mag
        :param kwargs: see :class:`SourceExtractionData`
        """
        # Defaults from SourceExtractionData
        super().__init__(source, **kwargs)

        if row is not None:
            # Override certain SourceExtractionData fields
            # with photometry-specific values
            self.x = row['x']
            self.y = row['y']
            self.flux = row['flux']

            # IPhotometry
            self.flux = row['flux']
            self.flux_error = row['flux_err']
            self.mag = row['mag'] + zero_point
            self.mag_error = row['mag_err']

            # IAperture
            if row['aper_a']:
                self.aper_a = row['aper_a']
                self.aper_b = row['aper_b']
                self.aper_theta = row['aper_theta']
                self.annulus_a_in = row['aper_a_in']
                self.annulus_b_in = \
                    row['aper_a_in']*row['aper_b_out']/row['aper_a_out']
                self.annulus_theta_in = self.annulus_theta_out = \
                    row['aper_theta_out']
                self.annulus_a_out = row['aper_a_out']
                self.annulus_b_out = row['aper_b_out']


class Photometry(AfterglowSchema):
    """
    Photometry results

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
