"""
Afterglow Access Server: source extraction job plugin
"""

from __future__ import absolute_import, division, print_function

from marshmallow.fields import Integer, List, Nested
from astropy.wcs import WCS

from skylib.extraction import extract_sources

from . import Job, JobResult
from .data_structures import SourceExtractionData, SourceExtractionSettings
from .source_merge_job import SourceMergeSettings, merge_sources
from ..data_files import (
    get_data_file, get_exp_length, get_gain, get_image_time, get_subframe)
from ... import Boolean


__all__ = ['SourceExtractionJob', 'run_source_extraction_job']


class SourceExtractionJobResult(JobResult):
    data = List(Nested(SourceExtractionData), default=[])  # type: list


def run_source_extraction_job(job, settings, job_file_ids):
    """
    Batch photometry job body; also used during photometric calibration

    :param Job job: job class instance
    :param .data_structures.SourceExtractionSettings settings: soruce
        extraction settings
    :param list job_file_ids: data file IDs to process

    :return: list of source extraction results
    :rtype: list[SourceExtractionData]
    """
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

    result_data = []
    for file_no, id in enumerate(job_file_ids):
        try:
            # Get image data
            pixels = get_subframe(
                job.user_id, id, settings.x, settings.y,
                settings.width, settings.height)

            hdr = get_data_file(job.user_id, id)[1]

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

            result_data += [
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
            job.update_progress((file_no + 1)/len(job_file_ids)*100)
        except Exception as e:
            job.add_error('Data file ID {}: {}'.format(id, e))

    return result_data


class SourceExtractionJob(Job):
    name = 'source_extraction'
    description = 'Extract Sources'
    result = Nested(
        SourceExtractionJobResult)  # type: SourceExtractionJobResult
    file_ids = List(Integer(), default=[])  # type: list
    source_extraction_settings = Nested(
        SourceExtractionSettings, default={})  # type: SourceExtractionSettings
    merge_sources = Boolean(default=True)  # type: bool
    source_merge_settings = Nested(
        SourceMergeSettings, default={})  # type: SourceMergeSettings

    def run(self):
        result_data = run_source_extraction_job(
            self, self.source_extraction_settings, self.file_ids)

        if self.file_ids and len(self.file_ids) > 1 and self.merge_sources:
            result_data = merge_sources(
                result_data, self.source_merge_settings, self.id)

        self.result.data = result_data
