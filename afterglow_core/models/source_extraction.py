"""
Afterglow Core: source extraction data models
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from marshmallow.fields import Integer, String
from numpy import sqrt, log, rad2deg, void
from astropy.wcs import WCS

from ..schemas import AfterglowSchema, DateTime, Float


__all__ = [
    'IAstrometry', 'IFwhm', 'ISourceId', 'ISourceMeta', 'SourceExtractionData',
    'sigma_to_fwhm'
]


sigma_to_fwhm = 2.0*sqrt(2*log(2))


class ISourceMeta(AfterglowSchema):
    """
    Metadata for the source::
        file_id: data file ID
        time: exposure start time
        filter: filter name
        telescope: telescope name
        exp_length: exposure length in seconds
    """
    file_id: int = Integer()
    time: datetime = DateTime()
    filter: str = String()
    telescope: str = String()
    exp_length: float = Float()


class IAstrometry(AfterglowSchema):
    ra_hours: float = Float()
    dec_degs: float = Float()
    pm_sky: float = Float()
    pm_pos_angle_sky: float = Float()
    x: float = Float()
    y: float = Float()
    pm_pixel: float = Float()
    pm_pos_angle_pixel: float = Float()
    pm_epoch: datetime = DateTime()
    flux: float = Float()
    sat_pixels = Integer()


class IFwhm(AfterglowSchema):
    fwhm_x: float = Float()
    fwhm_y: float = Float()
    theta: float = Float()


class ISourceId(AfterglowSchema):
    id: str = String()


class SourceExtractionData(ISourceMeta, IAstrometry, IFwhm, ISourceId):
    """
    Description of object returned by source extraction
    """
    def __init__(self, source: Optional[SourceExtractionData] = None,
                 row: Optional[void] = None, x0: int = 0, y0: int = 0,
                 wcs: Optional[WCS] = None, **kwargs):
        """
        Create source extraction data class instance from another source
        extraction data object or from a NumPy source table row

        :param source: create from another source extraction data object ("copy
            constructor")
        :param row: source table row
        :param x0: X offset to convert from source table coordinates to global
            image coordinates; used only with `row`
        :param y0: Y offset to convert from source table coordinates to global
            image coordinates; used only with `row`
        :param wcs: optional WCS structure; if present, compute RA/Dec; used
            only with `row`
        :param kwargs: see :class:`ISourceMeta` and :class:`ISourceId`
        """
        super().__init__(source, **kwargs)

        if row is not None:
            self.x = row['x'] + x0
            self.y = row['y'] + y0
            self.fwhm_x = row['a']*sigma_to_fwhm
            self.fwhm_y = row['b']*sigma_to_fwhm
            self.theta = rad2deg(row['theta'])
            self.flux = row['flux']
            try:
                self.sat_pixels = row['saturated']
            except ValueError:
                pass

        if wcs is not None:
            # Apply astrometric calibration
            self.ra_hours, self.dec_degs = wcs.all_pix2world(self.x, self.y, 1)
            self.ra_hours /= 15
