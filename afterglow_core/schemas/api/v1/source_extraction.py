"""
Afterglow Core: source extraction data structures
"""

from datetime import datetime

from marshmallow.fields import Integer, String
from numpy import sqrt, log, rad2deg

from ... import AfterglowSchema, DateTime, Float


__all__ = [
    'sigma_to_fwhm', 'IAstrometry', 'IFWHM', 'ISourceId', 'ISourceMeta',
    'SourceExtractionData',
]


sigma_to_fwhm = 2.0*sqrt(2*log(2))


class ISourceMeta(AfterglowSchema):
    file_id = Integer()  # type: int
    time = DateTime()  # type: datetime
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
    pm_epoch = DateTime()  # type: datetime
    flux = Float()  # type: float


class IFWHM(AfterglowSchema):
    fwhm_x = Float()  # type: float
    fwhm_y = Float()  # type: float
    theta = Float()  # type: float


class ISourceId(AfterglowSchema):
    id = String()  # type: str


class SourceExtractionData(ISourceMeta, IAstrometry, IFWHM, ISourceId):
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
        data.flux = row['flux']

        if wcs is not None:
            # Apply astrometric calibration
            data.ra_hours, data.dec_degs = wcs.all_pix2world(data.x, data.y, 1)
            data.ra_hours /= 15

        return data
