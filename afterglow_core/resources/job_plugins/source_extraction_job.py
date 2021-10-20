"""
Afterglow Core: source extraction job plugin
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested
from astropy.wcs import WCS

from skylib.extraction import extract_sources

from ...models import Job, JobResult, SourceExtractionData
from ...schemas import AfterglowSchema, Boolean, Float
from ..data_files import (
    get_data_file_data, get_exp_length, get_gain, get_image_time, get_subframe)
from .source_merge_job import SourceMergeSettings, merge_sources


__all__ = [
    'SourceExtractionJob', 'SourceExtractionSettings',
    'run_source_extraction_job',
]


class SourceExtractionSettings(AfterglowSchema):
    x: int = Integer(default=1)
    y: int = Integer(default=1)
    width: int = Integer(default=0)
    height: int = Integer(default=0)
    threshold: float = Float(default=2.5)
    bk_size: float = Float(default=1/64)
    bk_filter_size: int = Integer(default=3)
    fwhm: float = Float(default=0)
    ratio: float = Float(default=1)
    theta: float = Float(default=0)
    min_pixels: int = Integer(default=3)
    min_fwhm: float = Float(default=0.8)
    max_fwhm: float = Float(default=10)
    max_ellipticity: float = Float(default=2)
    deblend: bool = Boolean(default=False)
    deblend_levels: int = Integer(default=32)
    deblend_contrast: float = Float(default=0.005)
    gain: float = Float(default=None)
    clean: float = Float(default=1)
    centroid: bool = Boolean(default=True)
    limit: int = Integer(default=None)
    sat_level: float = Float(default=63000)
    discard_saturated: int = Integer(default=1)


class SourceExtractionJobResult(JobResult):
    data: TList[SourceExtractionData] = List(
        Nested(SourceExtractionData), default=[])


class SourceExtractionJob(Job):
    type = 'source_extraction'
    description = 'Extract Sources'

    result: SourceExtractionJobResult = Nested(
        SourceExtractionJobResult)
    file_ids: TList[int] = List(Integer(), default=[])
    source_extraction_settings: SourceExtractionSettings = Nested(
        SourceExtractionSettings, default={})
    merge_sources: bool = Boolean(default=True)
    source_merge_settings: SourceMergeSettings = Nested(
        SourceMergeSettings, default={})

    def run(self):
        result_data = run_source_extraction_job(
            self, self.source_extraction_settings, self.file_ids)

        if self.file_ids and len(self.file_ids) > 1 and self.merge_sources:
            result_data = merge_sources(
                result_data, self.source_merge_settings, self.id)

        self.result.data = result_data


def run_source_extraction_job(job: Job,
                              settings: SourceExtractionSettings,
                              job_file_ids: TList[int],
                              update_progress: bool = True) -> \
        TList[SourceExtractionData]:
    """
    Batch photometry job body; also used during photometric calibration

    :param job: job class instance
    :param settings: source extraction settings
    :param job_file_ids: data file IDs to process
    :param update_progress: set to False when called by another job (e.g. WCS
        calibration)

    :return: list of source extraction results
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
        min_fwhm=settings.min_fwhm,
        max_fwhm=settings.max_fwhm,
        max_ellipticity=settings.max_ellipticity,
        deblend=settings.deblend,
        deblend_levels=settings.deblend_levels,
        deblend_contrast=settings.deblend_contrast,
        clean=settings.clean,
        centroid=settings.centroid,
        discard_saturated=settings.discard_saturated,
    )

    result_data = []
    for file_no, id in enumerate(job_file_ids):
        try:
            # Get image data
            pixels = get_subframe(
                job.user_id, id, settings.x, settings.y,
                settings.width, settings.height)

            hdr = get_data_file_data(job.user_id, id)[1]

            if settings.gain is None:
                gain = get_gain(hdr)
            else:
                gain = settings.gain

            epoch = get_image_time(hdr)
            texp = get_exp_length(hdr)
            flt = hdr.get('FILTER')
            scope = hdr.get('TELESCOP')

            if settings.discard_saturated > 0:
                sat_img = pixels >= settings.sat_level
            else:
                sat_img = None

            # Extract sources
            source_table, background, background_rms = extract_sources(
                pixels, gain=gain, sat_img=sat_img, **extraction_kw)

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
                SourceExtractionData(
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
            if update_progress:
                job.update_progress((file_no + 1)/len(job_file_ids)*100)
        except Exception as e:
            job.add_error(e, {'file_id': id})

    return result_data
