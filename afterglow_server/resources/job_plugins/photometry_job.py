"""
Afterglow Access Server: batch photometry job plugin
"""

from __future__ import absolute_import, division, print_function

from datetime import datetime

from marshmallow.fields import Integer, List, Nested, String
from numpy import clip, cos, deg2rad, hypot, isfinite, sin, zeros
from astropy.wcs import WCS
import sep

from skylib.photometry import aperture_photometry
from skylib.extraction.centroiding import centroid_sources

from . import Job, JobResult
from .data_structures import SourceExtractionData, sigma_to_fwhm
from ..data_files import (
    get_data_file, get_exp_length, get_gain, get_image_time, get_phot_cal)
from ... import AfterglowSchema, Float


__all__ = ['PhotometryData', 'PhotometryJob', 'get_source_xy']


class PhotometryData(SourceExtractionData):
    """
    Description of object returned by batch photometry
    """
    mag = Float()  # type: float
    mag_error = Float()  # type: float
    flux = Float()  # type: float
    flux_error = Float()  # type: float

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
        data.flux = row['flux']
        data.flux_error = row['flux_err']
        data.mag = row['mag']
        data.mag_error = row['mag_err']

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


class PhotometryJobResult(JobResult):
    data = List(Nested(PhotometryData), default=[])  # type: list


def get_source_xy(source, epoch, wcs):
    """
    Calculate XY coordinates of a source in the current image, possibly taking
    proper motion into account

    :param SourceExtractionData source: source definition
    :param datetime.datetime epoch: exposure start time
    :param astropy.wcs.WCS wcs: WCS structure from image header

    :return: XY coordinates of the source, 1-based
    :rtype: tuple(float, float)
    """
    if None not in (source.ra_hours, source.dec_degs, wcs):
        # Prefer RA/Dec if WCS is present
        ra, dec = source.ra_hours*15, source.dec_degs
        if None not in [getattr(source, name, None)
                        for name in ('source.pm_sky', 'source.pm_pos_angle_sky',
                                     'source.pm_epoch', 'epoch')]:
            mu = source.pm_sky*(epoch - source.pm_epoch).total_seconds()
            theta = deg2rad(source.pm_pos_angle_sky)
            cd = cos(deg2rad(dec))
            return wcs.all_world2pix(
                ((ra + mu*sin(theta)/cd) if cd else ra) % 360,
                clip(dec + mu*cos(theta), -90, 90), 1)
        return wcs.all_world2pix(ra, dec, 1)

    if None not in [getattr(source, name, None)
                    for name in ('source.pm_pixel', 'source.pm_pos_angle_pixel',
                                 'source.pm_epoch', 'epoch')]:
        mu = source.pm_pixel*(epoch - source.pm_epoch).total_seconds()
        theta = deg2rad(source.pm_pos_angle_pixel)
        return source.x + mu*cos(theta), source.y + mu*sin(theta)

    return source.x, source.y


class PhotometryJob(Job):
    name = 'photometry'
    description = 'Photometer Sources'
    result = Nested(
        PhotometryJobResult, default={})  # type: PhotometryJobResult
    file_ids = List(Integer(), default=[])  # type: list
    sources = List(Nested(SourceExtractionData), default=[])  # type: list
    settings = Nested(PhotSettings, default={})  # type: PhotSettings

    def run(self):
        settings = self.settings

        if settings.mode == 'aperture':
            # Fixed-aperture photometry
            if settings.a is None:
                raise ValueError(
                    'Missing aperture radius/semi-major axis for '
                    'mode="aperture"')
            if settings.a <= 0:
                raise ValueError(
                    'Aperture radius/semi-major axis must be positive')
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
                k=settings.a if settings.a > 0 else 2.5,
                k_in=settings.a_in,
                k_out=settings.a_out,
            )

            # Make sure that all input sources have FWHMs
            if any(None in (source.fwhm_x, source.fwhm_y, source.theta)
                   for source in self.sources):
                raise ValueError('Missing FWHM data for automatic photometry')
        else:
            raise ValueError('Photometry mode must be "aperture" or "auto"')

        # Extract file IDs from sources
        file_ids = {source.file_id for source in self.sources
                    if getattr(source, 'file_id', None) is not None}
        if len(file_ids) < 2:
            # Same source object for all images specified in file_ids;
            # replicate each source to all images; merge them by assigning the
            # same source ID
            if not self.file_ids and not file_ids:
                raise ValueError('Missing data file IDs')
            if self.file_ids:
                file_ids |= set(self.file_ids)
            prefix = '{}_{}_'.format(
                datetime.utcnow().strftime('%Y%m%d%H%M%S'), self.id)
            sources = {
                file_id: [
                    SourceExtractionData(
                        source, file_id=file_id,
                        id=source.id if hasattr(source, 'id') and source.id
                        else prefix + str(i + 1))
                    for i, source in enumerate(self.sources)
                ] for file_id in file_ids
            }
        else:
            # Individual source object for each image; ignore file_ids
            if any(getattr(source, 'file_id', None) is None
                   for source in self.sources):
                raise ValueError('Missing data file ID for at least one source')
            sources = {}
            for source in self.sources:
                sources.setdefault(source.file_id, []).append(source)

        result_data = []
        for file_no, file_id in enumerate(file_ids):
            try:
                data, hdr = get_data_file(self.user_id, file_id)

                if settings.gain is None:
                    gain = get_gain(hdr)
                else:
                    gain = settings.gain
                if gain:
                    phot_kw['gain'] = gain

                epoch = get_image_time(hdr)
                texp = get_exp_length(hdr)
                phot_cal = get_phot_cal(hdr)
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
                for i, source in enumerate(sources[file_id]):
                    row = source_table[i]
                    row['x'], row['y'] = get_source_xy(source, epoch, wcs)
                if settings.mode == 'auto':
                    for i, source in enumerate(sources[file_id]):
                        row = source_table[i]
                        row['a'] = source.fwhm_x/sigma_to_fwhm
                        row['b'] = source.fwhm_y/sigma_to_fwhm
                        row['theta'] = source.theta
                    source_table['theta'] = deg2rad(source_table['theta'])

                if settings.centroid_radius > 0:
                    source_table['x'], source_table['y'] = centroid_sources(
                        data, source_table['x'], source_table['y'],
                        settings.centroid_radius)

                # Photometer all sources in the current image
                source_table = aperture_photometry(
                    data, source_table, **phot_kw)

                # Apply photometric calibration if present in data file
                if phot_cal:
                    try:
                        source_table['mag'] += phot_cal['m0']
                    except (KeyError, TypeError):
                        self.add_warning(
                            'Data file ID {}: Could not apply photometric '
                            'calibration'.format(file_id))
                    try:
                        source_table['mag_err'] = hypot(
                            source_table['mag_err'], phot_cal['m0_err'])
                    except (KeyError, TypeError):
                        self.add_warning(
                            'Data file ID {}: Could not calculate photometric '
                            'error'.format(file_id))

                # noinspection PyTypeChecker
                result_data += [
                    PhotometryData.from_phot_table(
                        row, source,
                        time=epoch,
                        filter=flt,
                        telescope=scope,
                        exp_length=texp,
                    )
                    for row, source in zip(source_table, sources[file_id])
                    if row['flag'] & (0xF0 & ~sep.APER_HASMASKED) == 0 and
                    isfinite([row['x'], row['y'], row['flux'], row['flux_err'],
                              row['mag'], row['mag_err']]).all()]
                self.update_progress((file_no + 1)/len(file_ids)*100)
            except Exception as e:
                self.add_error('Data file ID {}: {}'.format(file_id, e))

        self.result.data = result_data
