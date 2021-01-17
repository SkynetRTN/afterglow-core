"""
Afterglow Core: image alignment job plugin
"""

from typing import List as TList

from marshmallow.fields import String, Integer, List, Nested
from astropy.wcs import WCS

from skylib.combine.alignment import apply_transform_stars, apply_transform_wcs

from ...models import Job, JobResult, SourceExtractionData
from ...schemas import AfterglowSchema, Boolean
from ...errors import AfterglowError, ValidationError
from ..data_files import (
    create_data_file, get_data_file_data, get_data_file_db, get_root,
    save_data_file)
from .cropping_job import run_cropping_job


__all__ = ['AlignmentJob']


class AlignmentSettings(AfterglowSchema):
    ref_image: str = String(default='central')
    wcs_grid_points: int = Integer(default=0)
    prefilter: bool = Boolean(default=True)


class AlignmentJobResult(JobResult):
    file_ids: TList[int] = List(Integer(), default=[])


class AlignmentJob(Job):
    """
    Image alignment job
    """
    type = 'alignment'
    description = 'Align Images'

    result: AlignmentJobResult = Nested(AlignmentJobResult, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    settings: AlignmentSettings = Nested(AlignmentSettings, default={})
    sources: TList[SourceExtractionData] = List(
        Nested(SourceExtractionData), default=[])
    inplace: bool = Boolean(default=False)
    crop: bool = Boolean(default=False)

    def run(self):
        settings = self.settings

        # Load data files
        file_ids = list(self.file_ids)
        if not file_ids:
            return

        adb = get_data_file_db(self.user_id)
        try:
            # Get reference image index and the corresponding data file ID
            try:
                if settings.ref_image == 'first':
                    ref_image = 0
                elif settings.ref_image == 'last':
                    ref_image = len(file_ids) - 1
                elif settings.ref_image == 'central':
                    ref_image = len(file_ids)//2
                elif settings.ref_image.strip().startswith('#'):
                    # 0-based index in file_ids
                    ref_image = int(settings.ref_image.strip()[1:])
                    if not 0 <= ref_image < len(file_ids):
                        raise ValidationError(
                            'settings.ref_image',
                            'Reference image index out of range', 422)
                else:
                    # Data file ID
                    ref_image = int(settings.ref_image)
                    try:
                        ref_image = file_ids.index(ref_image)
                    except ValueError:
                        # Not in file_ids; implicitly add
                        file_ids.append(ref_image)
                        ref_image = len(file_ids) - 1
            except AfterglowError:
                raise
            except Exception:
                raise ValidationError(
                    'settings.ref_image',
                    'Reference image must be "first", "last", "central", or '
                    'data file ID, or #file_no', 422)
            ref_file_id = file_ids[ref_image]

            if self.sources:
                # Source-based alignment
                if any(not hasattr(source, 'file_id')
                       for source in self.sources):
                    raise ValueError(
                        'Missing data file ID for at least one source')

                # Extract alignment stars for reference image
                ref_sources = [
                    source for source in self.sources
                    if getattr(source, 'file_id', None) == ref_file_id]
                ref_stars = {getattr(source, 'id', None): (source.x, source.y)
                             for source in ref_sources}
                if not ref_stars:
                    raise ValueError(
                        'Missing alignment stars for reference image')
                if None in ref_stars and len(ref_sources) > 1:
                    # Cannot mix sources with and without ID
                    raise ValueError('Missing reference image source ID')
            else:
                # WCS-based alignment
                ref_stars = {}

            # Load data and extract WCS for reference image
            ref_data, ref_hdr = get_data_file_data(self.user_id, ref_file_id)
            ref_height, ref_width = ref_data.shape
            # noinspection PyBroadException
            try:
                ref_wcs = WCS(ref_hdr)
                if not ref_wcs.has_celestial:
                    ref_wcs = None
            except Exception:
                ref_wcs = None
            if ref_wcs is None and not ref_stars:
                raise ValueError('Reference image has no WCS')

            for i, file_id in enumerate(file_ids):
                try:
                    if i != ref_image:
                        # Load and transform the current image based on either
                        # star coordinates or WCS
                        data, hdr = get_data_file_data(self.user_id, file_id)
                        if ref_stars:
                            # Extract current image sources that are also
                            # present in the reference image
                            img_sources = [
                                source for source in self.sources
                                if getattr(source, 'file_id', None) == file_id]
                            img_stars = {getattr(source, 'id', None):
                                         (source.x, source.y)
                                         for source in img_sources}
                            if None in img_stars and len(img_sources) > 1:
                                raise ValueError('Missing source ID')
                            src_stars, dst_stars = [], []
                            for src_id, src_star in img_stars.items():
                                try:
                                    dst_star = ref_stars[src_id]
                                except KeyError:
                                    pass
                                else:
                                    src_stars.append(src_star)
                                    dst_stars.append(dst_star)
                            if not src_stars:
                                raise ValueError('Missing alignment star(s)')
                            data = apply_transform_stars(
                                data, src_stars, dst_stars, ref_width,
                                ref_height, prefilter=settings.prefilter)

                            nref = len(src_stars)
                            hist_msg = '{:d} star{}'.format(
                                nref, 's' if nref > 1 else '')

                        else:
                            # Extract current image WCS
                            # noinspection PyBroadException
                            try:
                                wcs = WCS(hdr)
                                if not wcs.has_celestial:
                                    wcs = None
                            except Exception:
                                wcs = None
                            if wcs is None:
                                raise ValueError('Missing WCS')

                            data = apply_transform_wcs(
                                data, wcs, ref_wcs, ref_width, ref_height,
                                grid_points=settings.wcs_grid_points,
                                prefilter=settings.prefilter)

                            hist_msg = 'WCS'

                        hdr.add_history(
                            'Aligned using {} with respect to data file '
                            '{:d}'.format(hist_msg, ref_file_id))

                        # Copy WCS from reference image if any
                        if ref_wcs is not None:
                            # Preserve epoch of observation
                            orig_kw = {
                                name: (hdr[name], hdr.comments[name])
                                if hdr.comments[name] else hdr[name]
                                for name in ('DATE-OBS', 'MJD-OBS')
                                if name in hdr
                            }

                            # Remove the possible alternative WCS
                            # representations to avoid WCS compatibility issues
                            # and make the WCS consistent
                            for name in (
                                    'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2',
                                    'PC1_1', 'PC1_2', 'PC2_1', 'PC2_2',
                                    'CDELT1', 'CDELT2', 'CROTA1', 'CROTA2'):
                                try:
                                    del hdr[name]
                                except KeyError:
                                    pass

                            hdr.update(ref_wcs.to_header(relax=True))
                            for name, val in orig_kw.items():
                                hdr[name] = val
                    else:
                        data, hdr = ref_data, ref_hdr

                    if not self.inplace:
                        # Don't create a new data file for reference image that
                        # was not listed in file_ids but was instead passed in
                        # settings.ref_image
                        if i != ref_image or ref_file_id in self.file_ids:
                            hdr.add_history(
                                'Original data file ID: {:d}'.format(file_id))
                            try:
                                file_id = create_data_file(
                                    adb, None, get_root(self.user_id), data,
                                    hdr, duplicates='append',
                                    session_id=self.session_id).id
                                adb.commit()
                            except Exception:
                                adb.rollback()
                                raise
                    elif i != ref_image:  # not replacing reference image
                        try:
                            save_data_file(
                                adb, get_root(self.user_id), file_id, data, hdr)
                            adb.commit()
                        except Exception:
                            adb.rollback()
                            raise

                    if i != ref_image or ref_file_id in self.file_ids:
                        self.result.file_ids.append(file_id)
                except Exception as e:
                    self.add_error(
                        'Data file ID {}: {}'.format(file_ids[i], e))
                finally:
                    self.update_progress((i + 1)/len(file_ids)*100)
        finally:
            adb.remove()

        # Optionally crop aligned files in place
        if self.crop:
            run_cropping_job(self, None, self.result.file_ids, inplace=True)
