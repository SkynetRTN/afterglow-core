"""
Afterglow Access Server: source extraction job plugin
"""

from __future__ import absolute_import, division, print_function

import datetime
from marshmallow.fields import Boolean, Float, Integer, List, Nested, String
from numpy import log, rad2deg, sqrt
from astropy.wcs import WCS
from skylib.extraction import extract_sources
from . import DateTime, Job, JobResult
from ..data_files import (
    UnknownDataFileError, get_data_file, get_exp_length, get_gain,
    get_image_time, get_subframe)
from ... import AfterglowSchema, errors


sigma_to_fwhm = 2.0*sqrt(2*log(2))


class HeaderData(AfterglowSchema):
    file_id = Integer()  # type: int
    time = DateTime()  # type: datetime.datetime
    filter = String()  # type: str
    telescope = String()  # type: str
    exp_length = Float()  # type: float


class Astrometry(AfterglowSchema):
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


class SourceExtractionData(HeaderData, Astrometry):
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
    gain = Float()  # type: float
    clean = Float(default=1)  # type: float
    centroid = Boolean(default=True)  # type: bool


class SourceExtractionJobResult(JobResult):
    data = List(Nested(SourceExtractionData), default=[])  # type: list


class SourceExtractionJob(Job):
    name = 'source_extraction'
    description = 'Extract Sources'
    result = Nested(
        SourceExtractionJobResult)  # type: SourceExtractionJobResult
    file_ids = List(Integer())  # type: list
    source_extraction_settings = Nested(
        SourceExtractionSettings, default={})  # type: SourceExtractionSettings

    def run(self):
        settings = self.source_extraction_settings

        extraction_kw = dict(
            threshold=settings.threshold,
            bkg_kw=dict(
                size=settings.bk_size,
                filter_size=settings.bk_filter_size,
            ),
            fwhm=settings.fwhm,
            ratio=settings.ratio,
            theta=settings.theta,
            min_pixels=settings.min_pixels,
            deblend=settings.deblend,
            deblend_levels=settings.deblend_levels,
            deblend_contrast=settings.deblend_contrast,
            clean=settings.clean,
            centroid=settings.centroid,
        )

        for file_no, id in enumerate(self.file_ids):
            try:
                # Get image data
                try:
                    pixels = get_subframe(
                        self.user_id, id, settings.x, settings.y,
                        settings.width, settings.height)
                except errors.AfterglowError:
                    raise
                except Exception:
                    raise UnknownDataFileError(id=id)

                hdr = get_data_file(self.user_id, id)[0].header

                if settings.gain is None:
                    gain = get_gain(hdr)
                else:
                    gain = settings.gain

                epoch = get_image_time(hdr)
                texp = get_exp_length(hdr)
                flt = hdr.get('FILTER')
                scope = hdr.get('TELESCOP')

                # Extract sources
                source_table, background, background_rms = extract_sources(
                    pixels, gain=gain, **extraction_kw)

                # Apply astrometric calibration if present
                # noinspection PyBroadException
                try:
                    wcs = WCS(hdr)
                    if not wcs.has_celestial:
                        wcs = None
                except Exception:
                    wcs = None

                self.result.data += [
                    SourceExtractionData.from_source_table(
                        row=row,
                        x0=settings.x,
                        y0=settings.y,
                        wcs=wcs,
                        file_id=id,
                        time=epoch,
                        filter=flt,
                        telescope=scope,
                        exp_length=texp,
                    )
                    for row in source_table]
                self.state.progress = (file_no + 1)/len(self.file_ids)*100
                self.update()
            except Exception as e:
                self.add_error('Data file ID {}: {}'.format(id, e))
