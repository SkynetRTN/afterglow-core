"""
Afterglow Core: photometry data models
"""

from typing import Optional

from marshmallow.fields import String
import numpy

from ..schemas import AfterglowSchema, Boolean, Float
from .source_extraction import SourceExtractionData


__all__ = [
    'IAperture', 'IPhotometry', 'Mag', 'Photometry', 'PhotometryData',
    'PhotSettings',
]


class Mag(AfterglowSchema):
    value: float = Float()
    error: float = Float()


class IPhotometry(AfterglowSchema):
    flux: float = Float()
    flux_error: float = Float()
    mag: Optional[float] = Float()
    mag_error: Optional[float] = Float()


class IAperture(AfterglowSchema):
    aper_a: float = Float()
    aper_b: float = Float()
    aper_theta: float = Float()
    annulus_a_in: float = Float()
    annulus_b_in: float = Float()
    annulus_theta_in: float = Float()
    annulus_a_out: float = Float()
    annulus_b_out: float = Float()
    annulus_theta_out: float = Float()


class PhotSettings(AfterglowSchema):
    mode: str = String(dump_default='aperture')
    a: float = Float(dump_default=None)
    b: float = Float(dump_default=None)
    theta: float = Float(dump_default=0)
    a_in: float = Float(dump_default=None)
    a_out: float = Float(dump_default=None)
    b_out: float = Float(dump_default=None)
    theta_out: float = Float(dump_default=None)
    gain: float = Float(dump_default=None)
    centroid_radius: float = Float(dump_default=0)
    zero_point: float = Float(dump_default=0)
    fix_aper: bool = Boolean(dump_default=False)
    fix_ell: bool = Boolean(dump_default=True)
    fix_rot: bool = Boolean(dump_default=True)
    apcorr_tol: float = Float(dump_default=0.0001)


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
        super().__init__(source, row, **kwargs)

        if row is not None:
            # IPhotometry
            self.flux = row['flux']
            self.flux_error = row['flux_err']
            if row['mag'] or row['mag_err']:
                self.mag = row['mag'] + zero_point
                self.mag_error = row['mag_err']
            else:
                self.mag = self.mag_error = None

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
        background: mean background within the annulus if local background is
            enabled; mean global background within the aperture otherwise

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
