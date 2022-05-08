"""
Afterglow Core: image property extraction job plugin
"""

from typing import List as TList

from numpy import median, sqrt
from astropy.wcs import WCS
from marshmallow.fields import Integer, List, Nested

from ...models import Job, JobResult, ImageProperties
from ..data_files import get_data_file_data, get_data_file_fits
from .source_extraction_job import (
    SourceExtractionSettings, run_source_extraction_job)


__all__ = ['ImagePropsExtractionJob']


class ImagePropsExtractionJobResult(JobResult):
    data: TList[ImageProperties] = List(Nested(ImageProperties), default=[])


class ImagePropsExtractionJob(Job):
    type = 'image_props'
    description = 'Extraction of Image Properties'

    result: ImagePropsExtractionJobResult = Nested(
        ImagePropsExtractionJobResult, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    source_extraction_settings: SourceExtractionSettings = Nested(
        SourceExtractionSettings, default=None)

    def run(self):
        if not getattr(self, 'file_ids', None):
            return

        # Disable centroiding; will be done separately by PSF fitting
        source_extraction_settings = self.source_extraction_settings or \
            SourceExtractionSettings(_set_defaults=True)
        source_extraction_settings.centroid = False

        for file_no, file_id in enumerate(self.file_ids):
            try:
                # Detect sources using the settings provided
                sources, background_info = run_source_extraction_job(
                    self, source_extraction_settings, [file_id],
                    update_progress=False)
                if not sources:
                    raise RuntimeError('Could not detect any sources')
                background, background_rms = background_info.get(
                    file_id, (None, None))
                global_snr = sqrt((((
                    get_data_file_data(self.user_id, file_id)[0] -
                    background)/background_rms)**2).mean())
                if background is not None:
                    background = background.mean()
                if background_rms is not None:
                    background_rms = background_rms.mean()

                # Calculate the median of FWHMs along the minor axis
                seeing_pixels = median([source.fwhm_y for source in sources])

                # Calculate median ellipticity
                ellipticity = median([1 - source.fwhm_y/source.fwhm_x
                                      for source in sources])

                # Convert seeing to arcsecs if pixel scale is available
                with get_data_file_fits(self.user_id, file_id) as f:
                    hdr = f[0].header
                # noinspection PyBroadException
                try:
                    wcs = WCS(hdr)
                    if not wcs.has_celestial:
                        wcs = None
                except Exception:
                    wcs = None
                if wcs is None:
                    scale = hdr.get('SECPIX')
                else:
                    scales = wcs.proj_plane_pixel_scales()
                    scale = (scales[0].to('arcsec').value +
                             scales[1].to('arcsec').value)/2
                if scale:
                    seeing_arcsec = seeing_pixels*scale
                else:
                    seeing_arcsec = None

                self.result.data.append(ImageProperties(
                    file_id=file_id,
                    background_counts=background,
                    background_rms_counts=background_rms,
                    num_sources=len(sources),
                    num_saturated_sources=len(
                        [source for source in sources
                         if getattr(source, 'sat_pixels', 0)]),
                    seeing_pixels=seeing_pixels,
                    seeing_arcsec=seeing_arcsec,
                    ellipticity=ellipticity,
                    global_snr=global_snr,
                ))

            except Exception as e:
                self.add_error(e, {'file_id': file_id})
            finally:
                self.update_progress((file_no + 1)/len(self.file_ids)*100)
