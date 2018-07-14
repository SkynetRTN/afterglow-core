"""
Afterglow Access Server: source extraction job plugin
"""

from __future__ import absolute_import, division, print_function

from marshmallow.fields import Float, Integer, List, Nested
from astropy.wcs import WCS
from skylib.extraction import extract_sources
from . import Boolean, Job, JobResult
from .data_structures import SourceExtractionData
from .source_merge_job import SourceMergeSettings, merge_sources
from ..data_files import (
    get_data_file, get_exp_length, get_gain, get_image_time, get_subframe)
from ... import AfterglowSchema


__all__ = ['SourceExtractionJob']


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
    limit = Integer()  # type: int


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
    merge_sources = Boolean(default=True)  # type: bool
    source_merge_settings = Nested(
        SourceMergeSettings, default={})  # type: SourceMergeSettings

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

        do_merge = self.file_ids and len(self.file_ids) > 1 and \
            self.merge_sources

        for file_no, id in enumerate(self.file_ids):
            try:
                # Get image data
                pixels = get_subframe(
                    self.user_id, id, settings.x, settings.y,
                    settings.width, settings.height)

                hdr = get_data_file(self.user_id, id)[1]

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

                if settings.limit and len(source_table) > settings.limit:
                    # Leave only the given number of the brightest sources
                    source_table.sort(order='flux')
                    source_table = source_table[:-(settings.limit + 1):-1]

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
                self.state.progress = (file_no + 1)/len(self.file_ids)*(
                    100 - 10*do_merge)
                self.update()
            except Exception as e:
                self.add_error('Data file ID {}: {}'.format(id, e))

        if do_merge:
            self.result.data = merge_sources(
                self.result.data, self.source_merge_settings, self.id)
