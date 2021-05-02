"""
Afterglow Core: batch photometry job plugin
"""

from datetime import datetime
from typing import List as TList, Tuple

from marshmallow.fields import Integer, List, Nested
from numpy import clip, concatenate, cos, deg2rad, isfinite, sin, zeros
from astropy.wcs import WCS
import sep

from skylib.photometry import aperture_photometry
from skylib.extraction.centroiding import centroid_sources

from ...models import (
    Job, JobResult, SourceExtractionData, PhotSettings, PhotometryData,
    sigma_to_fwhm)
from ..data_files import (
    get_data_file_data, get_exp_length, get_gain, get_image_time)


__all__ = ['PhotometryJob', 'get_source_xy', 'run_photometry_job']


def get_source_xy(source: SourceExtractionData, epoch: datetime, wcs: WCS) \
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
                clip(dec + mu*cos(theta), -90, 90), 1)
        return wcs.all_world2pix(ra, dec, 1)

    if None not in [getattr(source, name, None)
                    for name in ('pm_pixel', 'pm_pos_angle_pixel',
                                 'pm_epoch', 'epoch')]:
        mu = source.pm_pixel*(epoch - source.pm_epoch).total_seconds()
        theta = deg2rad(source.pm_pos_angle_pixel)
        return source.x + mu*cos(theta), source.y + mu*sin(theta)

    return source.x, source.y


def run_photometry_job(job: Job, settings: PhotSettings,
                       job_file_ids: TList[int],
                       job_sources: TList[SourceExtractionData]) \
        -> TList[PhotometryData]:
    """
    Batch photometry job body; also used during photometric calibration

    :param job: job class instance
    :param settings: photometry settings
    :param job_file_ids: data file IDs to process
    :param job_sources: list of SourceExtractionData-compatible source defs

    :return: list of photometry results
    """
    if not job_sources:
        return []

    if settings.mode == 'aperture':
        # Fixed-aperture photometry
        if settings.a is None:
            raise ValueError(
                'Missing aperture radius/semi-major axis for mode="aperture"')
        if settings.a <= 0:
            raise ValueError('Aperture radius/semi-major axis must be positive')
        phot_kw = dict(
            a=settings.a,
            b=settings.b,
            theta=settings.theta,
            a_in=settings.a_in,
            a_out=settings.a_out,
            b_out=settings.b_out,
            theta_out=settings.theta_out,
        )
    elif settings.mode == 'auto':
        # Automatic (Kron-like) photometry
        phot_kw = dict(
            k=settings.a if settings.a else 2.5,
            k_in=settings.a_in,
            k_out=settings.a_out,
            fix_aper=settings.fix_aper,
            fix_ell=settings.fix_ell,
            fix_rot=settings.fix_rot,
        )
    else:
        raise ValueError('Photometry mode must be "aperture" or "auto"')

    # Extract file IDs from sources
    file_ids = {source.file_id for source in job_sources
                if getattr(source, 'file_id', None) is not None}
    if not file_ids:
        # Same source object for all images specified in file_ids;
        # replicate each source to all images; merge them by assigning the
        # same source ID
        if not job_file_ids and not file_ids:
            raise ValueError('Missing data file IDs')
        if job_file_ids:
            file_ids = set(job_file_ids)
        prefix = '{}_{}_'.format(
            datetime.utcnow().strftime('%Y%m%d%H%M%S'), job.id)
        sources = {
            file_id: [
                SourceExtractionData(
                    source=source, file_id=file_id,
                    id=source.id if hasattr(source, 'id') and source.id
                    else prefix + str(i + 1))
                for i, source in enumerate(job_sources)
            ] for file_id in file_ids
        }
    else:
        # Individual source object for each image; ignore job_file_ids
        if any(getattr(source, 'file_id', None) is None
               for source in job_sources):
            raise ValueError('Missing data file ID for at least one source')
        sources = {}
        for source in job_sources:
            sources.setdefault(source.file_id, []).append(source)

    # Apply custom zero point to instrumental mags if requested
    m0 = getattr(settings, 'zero_point', None) or 0

    result_data = []
    for file_no, file_id in enumerate(file_ids):
        try:
            data, hdr = get_data_file_data(job.user_id, file_id)

            if settings.gain is None:
                gain = get_gain(hdr)
            else:
                gain = settings.gain
            if gain:
                phot_kw['gain'] = gain

            epoch = get_image_time(hdr)
            texp = get_exp_length(hdr)
            flt = hdr.get('FILTER')
            scope = hdr.get('TELESCOP')

            if texp:
                phot_kw['texp'] = texp

            # noinspection PyBroadException
            try:
                wcs = WCS(hdr)
                if not wcs.has_celestial:
                    wcs = None
            except Exception:
                wcs = None

            source_table = zeros(
                len(sources[file_id]),
                [('x', float), ('y', float), ('a', float), ('b', float),
                 ('theta', float), ('flux', float), ('saturated', int),
                 ('flag', int)])
            i = 0
            while i < len(sources[file_id]):
                x, y = get_source_xy(sources[file_id][i], epoch, wcs)
                if 0 <= x < data.shape[1] and 0 <= y < data.shape[0]:
                    source_table[i]['x'], source_table[i]['y'] = x, y
                    i += 1
                else:
                    # Source outside image boundaries, skip
                    del sources[file_id][i]
                    if i:
                        if i < len(source_table) - 1:
                            source_table = concatenate(
                                [source_table[:i], source_table[i + 1:]])
                        else:
                            source_table = source_table[:i]
                    else:
                        source_table = source_table[1:]
            if not sources[file_id]:
                raise ValueError('All sources are outside image boundaries')

            r_cent = settings.centroid_radius
            if settings.mode == 'auto':
                # We need the ellipse parameters for adaptive photometry;
                # derive them from the FWHMs if available, otherwise SkyLib
                # will estimate them by isophotal analysis
                phot_kw['radius'] = r_cent
                for i, source in enumerate(sources[file_id]):
                    row = source_table[i]
                    row['a'] = getattr(source, 'fwhm_x', None) or 0
                    row['b'] = getattr(source, 'fwhm_y', None) or 0
                    row['theta'] = getattr(source, 'theta', None) or 0
                    if (not row['a'] or not row['b']) and r_cent <= 0:
                        raise ValueError(
                            'Centroiding radius must be provided for '
                            'adaptive photometry with no FWHM info')
                source_table['a'] /= sigma_to_fwhm
                source_table['b'] /= sigma_to_fwhm
                source_table['theta'] = deg2rad(source_table['theta'])

            if r_cent > 0:
                # Obtain the accurate centroids if requested
                source_table['x'], source_table['y'] = centroid_sources(
                    data, source_table['x'], source_table['y'], r_cent)

            # Photometer all sources in the current image
            source_table = aperture_photometry(data, source_table, **phot_kw)

            result_data += [
                PhotometryData(
                    source=source,
                    row=row,
                    time=epoch,
                    filter=flt,
                    telescope=scope,
                    exp_length=texp,
                    zero_point=m0,
                )
                for row, source in zip(source_table, sources[file_id])
                if row['flag'] & (0xF0 & ~sep.APER_HASMASKED) == 0 and
                isfinite([row['x'], row['y'], row['flux'], row['flux_err'],
                          row['mag'], row['mag_err']]).all()]
            job.update_progress((file_no + 1)/len(file_ids)*100)
        except Exception as e:
            job.add_error('Data file ID {}: {}'.format(file_id, e))

    return result_data


class PhotometryJobResult(JobResult):
    data: TList[PhotometryData] = List(Nested(PhotometryData), default=[])


class PhotometryJob(Job):
    type = 'photometry'
    description = 'Photometer Sources'

    result: PhotometryJobResult = Nested(PhotometryJobResult, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    sources: TList[SourceExtractionData] = List(
        Nested(SourceExtractionData), default=[])
    settings: PhotSettings = Nested(PhotSettings, default={})

    def run(self):
        self.result.data = run_photometry_job(
            self, self.settings, self.file_ids, self.sources)
