"""
Afterglow Core: source extraction data models
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from marshmallow.fields import Integer, String
from numpy import clip, cos, deg2rad, log, rad2deg, sin, sqrt, void
from astropy.wcs import WCS

from ..schemas import AfterglowSchema, DateTime, Float


__all__ = [
    'IAstrometry', 'IFwhm', 'ISourceId', 'ISourceMeta', 'SourceExtractionData',
    'sigma_to_fwhm', 'get_source_radec', 'get_source_xy',
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
                 row: Optional[void] = None, ofs_x: int = 0, ofs_y: int = 0,
                 wcs: Optional[WCS] = None, **kwargs):
        """
        Create source extraction data class instance from another source
        extraction data object or from a NumPy source table row

        :param source: create from another source extraction data object ("copy
            constructor")
        :param row: source table row
        :param ofs_x: X offset to convert from source table coordinates
            to global image coordinates; used only with `row`
        :param ofs_y: Y offset to convert from source table coordinates
            to global image coordinates; used only with `row`
        :param wcs: optional WCS structure; if present, compute RA/Dec; used
            only with `row`
        :param kwargs: see :class:`ISourceMeta` and :class:`ISourceId`
        """
        super().__init__(source, **kwargs)

        if row is not None:
            self.x = row['x'] + ofs_x
            self.y = row['y'] + ofs_y
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
            self.ra_hours %= 360
            self.ra_hours /= 15


def get_source_xy(source, epoch: datetime, wcs: Optional[WCS]) \
        -> Tuple[float, float]:
    """
    Calculate XY coordinates of a source in the current image, possibly taking
    proper motion into account

    :param source: source definition
    :param epoch: exposure start time
    :param wcs: WCS structure from image header

    :return: XY coordinates of the source, 1-based
    """
    if None not in (getattr(source, 'ra_hours', None),
                    getattr(source, 'dec_degs', None), wcs):
        # Prefer RA/Dec if WCS is present
        ra, dec = source.ra_hours*15, source.dec_degs
        if epoch is not None and None not in [
                getattr(source, name, None)
                for name in ('pm_sky', 'pm_pos_angle_sky', 'pm_epoch')]:
            mu = source.pm_sky*(epoch - source.pm_epoch).total_seconds()
            theta = deg2rad(source.pm_pos_angle_sky)
            cd = cos(deg2rad(dec))
            return wcs.all_world2pix(
                ((ra + mu*sin(theta)/cd) if cd else ra) % 360,
                clip(dec + mu*cos(theta), -90, 90), 1, quiet=True)
        return wcs.all_world2pix(ra, dec, 1, quiet=True)

    if epoch is not None and None not in [
            getattr(source, name, None)
            for name in ('pm_pixel', 'pm_pos_angle_pixel', 'pm_epoch')]:
        mu = source.pm_pixel*(epoch - source.pm_epoch).total_seconds()
        theta = deg2rad(source.pm_pos_angle_pixel)
        return source.x + mu*cos(theta), source.y + mu*sin(theta)

    return source.x, source.y


def get_source_radec(source, epoch: datetime, wcs: Optional[WCS]) \
        -> Tuple[float, float]:
    """
    Calculate RA and Dec of a source in the current image, possibly taking
    proper motion into account

    :param source: source definition
    :param epoch: exposure start time
    :param wcs: WCS structure from image header

    :return: RA in hours, Dec in degrees
    """
    if None not in (getattr(source, 'ra_hours', None),
                    getattr(source, 'dec_degs', None)):
        ra, dec = source.ra_hours, source.dec_degs
        if epoch is not None and None not in [
                getattr(source, name, None)
                for name in ('pm_sky', 'pm_pos_angle_sky', 'pm_epoch')]:
            mu = source.pm_sky*(epoch - source.pm_epoch).total_seconds()
            theta = deg2rad(source.pm_pos_angle_sky)
            cd = cos(deg2rad(dec))
            return float(((ra + mu/15*sin(theta)/cd) if cd else ra) % 24), \
                float(clip(dec + mu*cos(theta), -90, 90))
        return ra, dec

    if None in [getattr(source, name, None)
                for name in ('pm_pixel', 'pm_pos_angle_pixel', 'pm_epoch')]:
        ra, dec = wcs.all_pix2world(source.x, source.y, 1)
    else:
        mu = source.pm_pixel*(epoch - source.pm_epoch).total_seconds()
        theta = deg2rad(source.pm_pos_angle_pixel)
        ra, dec = wcs.all_pix2world(
            source.x + mu*cos(theta), source.y + mu*sin(theta), 1)
    return (ra % 360)/15, dec
