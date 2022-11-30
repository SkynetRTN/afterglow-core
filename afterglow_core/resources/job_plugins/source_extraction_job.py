"""
Afterglow Core: source extraction job plugin
"""

from typing import Dict as TDict, List as TList, Tuple

from marshmallow.fields import Integer, List, Nested
from numpy import ndarray
from astropy.wcs import WCS

from skylib.extraction import auto_sat_level, extract_sources

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
    x: int = Integer(dump_default=1)
    y: int = Integer(dump_default=1)
    width: int = Integer(dump_default=0)
    height: int = Integer(dump_default=0)
    threshold: float = Float(dump_default=2.5)
    bk_size: float = Float(dump_default=1/64)
    bk_filter_size: int = Integer(dump_default=3)
    fwhm: float = Float(dump_default=0)
    ratio: float = Float(dump_default=1)
    theta: float = Float(dump_default=0)
    min_pixels: int = Integer(dump_default=3)
    min_fwhm: float = Float(dump_default=0.8)
    max_fwhm: float = Float(dump_default=10)
    max_ellipticity: float = Float(dump_default=2)
    deblend: bool = Boolean(dump_default=False)
    deblend_levels: int = Integer(dump_default=32)
    deblend_contrast: float = Float(dump_default=0.005)
    gain: float = Float(dump_default=None)
    clean: float = Float(dump_default=1)
    centroid: bool = Boolean(dump_default=True)
    limit: int = Integer(dump_default=None)
    sat_level: float = Float(dump_default=63000)
    auto_sat_level: bool = Boolean(dump_default=False)
    discard_saturated: int = Integer(dump_default=1)
    max_sources: int = Integer(dump_default=10000)


class SourceExtractionJobResult(JobResult):
    data: TList[SourceExtractionData] = List(
        Nested(SourceExtractionData), dump_default=[])


class SourceExtractionJob(Job):
    type = 'source_extraction'
    description = 'Extract Sources'

    result: SourceExtractionJobResult = Nested(
        SourceExtractionJobResult)
    file_ids: TList[int] = List(Integer(), dump_default=[])
    source_extraction_settings: SourceExtractionSettings = Nested(
        SourceExtractionSettings, dump_default={})
    merge_sources: bool = Boolean(dump_default=True)
    source_merge_settings: SourceMergeSettings = Nested(
        SourceMergeSettings, dump_default={})

    def run(self):
        result_data = run_source_extraction_job(
            self, self.source_extraction_settings, self.file_ids)[0]

        if self.file_ids and len(self.file_ids) > 1 and self.merge_sources:
            result_data = merge_sources(
                result_data, self.source_merge_settings, self.id)

        object.__setattr__(self.result, 'data', result_data)


def run_source_extraction_job(job: Job,
                              settings: SourceExtractionSettings,
                              job_file_ids: TList[int],
                              stage: int = 0, total_stages: int = 1) -> \
        Tuple[TList[SourceExtractionData],
              TDict[int, Tuple[ndarray, ndarray]]]:
    """
    Batch photometry job body; also used during photometric calibration

    :param job: job class instance
    :param settings: source extraction settings
    :param job_file_ids: data file IDs to process
    :param stage: optional processing stage number; used to properly update
        the job progress if cropping is a part of other job
    :param total_stages: total number of stages in the enclosing job if any;
        set to 0 to disable progress updates

    :return: list of source extraction results plus background and RMS map
        pairs indexed by file IDs
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
        max_sources=settings.max_sources,
    )

    result_data = []
    backgrounds = {}
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
                if settings.auto_sat_level:
                    sat_level = auto_sat_level(pixels)
                    if sat_level is None:
                        sat_level = settings.sat_level
                else:
                    sat_level = settings.sat_level
                sat_img = pixels >= sat_level
            else:
                sat_img = None

            # Extract sources
            source_table, background, background_rms = extract_sources(
                pixels, gain=gain, sat_img=sat_img, **extraction_kw)
            backgrounds[id] = (background, background_rms)

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
                    ofs_x=settings.x - 1,
                    ofs_y=settings.y - 1,
                    wcs=wcs,
                    file_id=id,
                    time=epoch,
                    filter=flt,
                    telescope=scope,
                    exp_length=texp,
                )
                for row in source_table]
            if total_stages:
                job.update_progress(
                    (file_no + 1)/len(job_file_ids)*100, stage, total_stages)
        except Exception as e:
            job.add_error(e, {'file_id': id})

    return result_data, backgrounds
