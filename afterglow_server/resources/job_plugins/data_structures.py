"""
Afterglow Access Server: data structures common to multiple job plugins
"""

from __future__ import absolute_import, division, print_function

import datetime

from marshmallow.fields import Dict, Integer, String
from numpy import log, rad2deg, sqrt

from ... import AfterglowSchema, Boolean, DateTime, Float


__all__ = [
    'IAstrometry', 'IPhotometry', 'ISourceId', 'ISourceMeta', 'ICatalogSource',
    'SourceExtractionSettings', 'SourceExtractionData', 'PhotSettings',
    'PhotometryData', 'CatalogSource',
    'sigma_to_fwhm',
]


sigma_to_fwhm = 2.0*sqrt(2*log(2))


class ISourceMeta(AfterglowSchema):
    file_id = Integer()  # type: int
    time = DateTime()  # type: datetime.datetime
    filter = String()  # type: str
    telescope = String()  # type: str
    exp_length = Float()  # type: float


class IAstrometry(AfterglowSchema):
    ra_hours = Float()  # type: float
    dec_degs = Float()  # type: float
    pm_sky = Float()  # type: float
    pm_pos_angle_sky = Float()  # type: float
    x = Float()  # type: float
    y = Float()  # type: float
    pm_pixel = Float()  # type: float
    pm_pos_angle_pixel = Float()  # type: float
    pm_epoch = DateTime()  # type: datetime.datetime
    fwhm_x = Float()  # type: float
    fwhm_y = Float()  # type: float
    theta = Float()  # type: float


class IPhotometry(AfterglowSchema):
    mag = Float()  # type: float
    mag_error = Float()  # type: float


class ISourceId(AfterglowSchema):
    id = String()  # type: str


class ICatalogSource(AfterglowSchema):
    """
    Generic catalog source definition without astrometry
    """
    id = String()  # type: str
    file_id = Integer()  # type: int
    label = String()  # type: str
    catalog_name = String()  # type: str
    mags = Dict()  # type: dict


class SourceExtractionSettings(AfterglowSchema):
    x = Integer(default=1)  # type: int
    y = Integer(default=1)  # type: int
    width = Integer(default=0)  # type: int
    height = Integer(default=0)  # type: int
    threshold = Float(default=2.5)  # type: float
    bk_size = Float(default=1/64)  # type: float
    bk_filter_size = Integer(default=3)  # type: int
    fwhm = Float(default=0)  # type: float
    ratio = Float(default=1)  # type: float
    theta = Float(default=0)  # type: float
    min_pixels = Integer(default=3)  # type: int
    deblend = Boolean(default=False)  # type: bool
    deblend_levels = Integer(default=32)  # type: int
    deblend_contrast = Float(default=0.005)  # type: float
    gain = Float(default=None)  # type: float
    clean = Float(default=1)  # type: float
    centroid = Boolean(default=True)  # type: bool
    limit = Integer(default=None)  # type: int


class SourceExtractionData(ISourceMeta, IAstrometry, ISourceId):
    """
    Description of object returned by source extraction
    """
    @classmethod
    def from_source_table(cls, row, x0, y0, wcs, **kwargs):
        """
        Create source extraction data class instance from a source table row

        :param numpy.void row: source table row
        :param int x0: X offset to convert from source table coordinates to
            global image coordinates
        :param int y0: Y offset to convert from source table coordinates to
            global image coordinates
        :param astropy.wcs.WCS wcs: optional WCS structure; if present, compute
            RA/Dec
        :param kwargs::
            file_id: data file ID
            time: exposure start time
            filter: filter name
            telescope: telescope name
            exp_length: exposure length in seconds
        """
        data = cls(**kwargs)

        data.x = row['x'] + x0
        data.y = row['y'] + y0
        data.fwhm_x = row['a']*sigma_to_fwhm
        data.fwhm_y = row['b']*sigma_to_fwhm
        data.theta = rad2deg(row['theta'])

        if wcs is not None:
            # Apply astrometric calibration
            data.ra_hours, data.dec_degs = wcs.all_pix2world(data.x, data.y, 1)
            data.ra_hours /= 15

        return data


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
        data.mag = row['mag']
        data.mag_error = row['mag_err']

        return data


class CatalogSource(ICatalogSource, IAstrometry, IPhotometry):
    """
    Catalog source definition for field calibration
    """
    pass
