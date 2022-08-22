"""
Afterglow Core: image alignment job plugin
"""

from datetime import datetime
from typing import List as TList

from numpy.ma import MaskedArray
from marshmallow.fields import String, Integer, List, Nested
from astropy.wcs import WCS
import cv2 as cv

from skylib.combine.alignment import *
from skylib.combine.pattern_matching import pattern_match

from ...models import Job, JobResult, SourceExtractionData
from ...schemas import AfterglowSchema, Boolean, Float, NestedPoly
from ...errors import AfterglowError, ValidationError
from ..data_files import (
    create_data_file, get_data_file_data, get_data_file_db, get_root,
    save_data_file)
from .cropping_job import run_cropping_job


__all__ = ['AlignmentJob']


class AlignmentSettings(AfterglowSchema):
    __polymorphic_on__ = 'mode'

    mode: str = String(dump_default='WCS', load_default='WCS')
    ref_image: str = String(dump_default='central')
    prefilter: bool = Boolean(dump_default=True)
    enable_rot: bool = Boolean(dump_default=True)
    enable_scale: bool = Boolean(dump_default=True)
    enable_skew: bool = Boolean(dump_default=True)


class AlignmentSettingsWCS(AlignmentSettings):
    mode = 'WCS'
    wcs_grid_points: int = Integer(dump_default=0)


class AlignmentSettingsSources(AlignmentSettings):
    mode = 'sources'
    sources: TList[SourceExtractionData] = List(
        Nested(SourceExtractionData), dump_default=[])
    max_sources: int = Integer(dump_default=100)
    scale_invariant: bool = Boolean(dump_default=False)
    match_tol: float = Float(dump_default=0.002)
    min_edge: float = Float(dump_default=0.003)
    ratio_limit: float = Float(dump_default=10)
    confidence: float = Float(dump_default=0.15)


class AlignmentSettingsFeatures(AlignmentSettings):
    __polymorphic_on__ = 'algorithm'

    mode = 'features'

    algorithm: str = String(dump_default='WCS', load_default='AKAZE')
    ratio_threshold: float = Float(dump_default=0.7)
    detect_edges: bool = Boolean(dump_default=False)


class AlignmentSettingsFeaturesAKAZE(AlignmentSettingsFeatures):
    algorithm = 'AKAZE'
    descriptor_type: str = String(dump_default='MLDB')
    descriptor_size: int = Integer(dump_default=0)
    descriptor_channels: int = Integer(dump_default=3)
    threshold: float = Float(dump_default=0.001)
    octaves: int = Integer(dump_default=4)
    octave_layers: int = Integer(dump_default=4)
    diffusivity: str = String(dump_default='PM_G2')


class AlignmentSettingsFeaturesBRISK(AlignmentSettingsFeatures):
    algorithm = 'BRISK'
    threshold: int = Integer(dump_default=30)
    octaves: int = Integer(dump_default=3)
    pattern_scale: float = Float(dump_default=1)


class AlignmentSettingsFeaturesKAZE(AlignmentSettingsFeatures):
    algorithm = 'KAZE'
    extended: bool = Boolean(dump_default=False)
    upright: bool = Boolean(dump_default=False)
    threshold: float = Float(dump_default=0.001)
    octaves: int = Integer(dump_default=4)
    octave_layers: int = Integer(dump_default=4)
    diffusivity: str = String(dump_default='PM_G2')


class AlignmentSettingsFeaturesORB(AlignmentSettingsFeatures):
    algorithm = 'ORB'
    nfeatures: int = Integer(dump_default=500)
    scale_factor: float = Float(dump_default=1.2)
    nlevels: int = Integer(dump_default=8)
    edge_threshold: int = Integer(dump_default=31)
    first_level: int = Integer(dump_default=0)
    wta_k: int = Integer(dump_default=2)
    score_type: str = String(dump_default='Harris')
    patch_size: int = Integer(dump_default=31)
    fast_threshold: int = Integer(dump_default=20)


class AlignmentSettingsFeaturesSIFT(AlignmentSettingsFeatures):
    algorithm = 'SIFT'
    nfeatures: int = Integer(dump_default=0)
    octave_layers: int = Integer(dump_default=3)
    contrast_threshold: float = Float(dump_default=0.04)
    edge_threshold: float = Float(dump_default=10)
    sigma: float = Float(dump_default=1.6)
    descriptor_type: str = String(dump_default='32F')


class AlignmentSettingsFeaturesSURF(AlignmentSettingsFeatures):
    algorithm = 'SURF'
    hessian_threshold: float = Float(dump_default=100)
    octaves: int = Integer(dump_default=4)
    octave_layers: int = Integer(dump_default=3)
    extended: bool = Boolean(dump_default=False)
    upright: bool = Boolean(dump_default=False)


class AlignmentSettingsPixels(AlignmentSettings):
    mode = 'pixels'
    detect_edges: bool = Boolean(dump_default=False)


class AlignmentJobResult(JobResult):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class AlignmentJob(Job):
    """
    Image alignment job
    """
    type = 'alignment'
    description = 'Align Images'

    result: AlignmentJobResult = Nested(AlignmentJobResult, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: AlignmentSettings = NestedPoly(
        AlignmentSettings, dump_default={})
    inplace: bool = Boolean(dump_default=False)
    crop: bool = Boolean(dump_default=False)

    def run(self):
        settings = self.settings

        # Load data files
        file_ids = list(self.file_ids)
        if not file_ids:
            return

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

        alignment_kwargs = {}
        ref_stars = anonymous_ref_stars = []

        if isinstance(settings, AlignmentSettingsSources):
            # Source-based alignment
            if any(not hasattr(source, 'file_id')
                   for source in settings.sources):
                raise ValueError(
                    'Missing data file ID for at least one source')

            # Extract alignment stars for reference image
            ref_sources = [
                source for source in settings.sources
                if getattr(source, 'file_id', None) == ref_file_id]
            if not ref_sources:
                raise ValueError(
                    'Missing alignment stars for reference image')
            ref_stars = {source.id: (source.x, source.y)
                         for source in ref_sources
                         if getattr(source, 'id', None) is not None}
            anonymous_ref_stars = [(source.x, source.y)
                                   for source in ref_sources
                                   if getattr(source, 'id', None) is None]
            if ref_stars and anonymous_ref_stars:
                # Cannot mix sources with and without ID
                raise ValueError(
                    'All or none of the reference image source must have '
                    'source ID')
            if len(anonymous_ref_stars) > settings.max_sources:
                # Too many stars for pattern matching; sort by brightness and
                # use at most max_sources stars
                ref_sources.sort(
                    key=lambda source: getattr(
                        source, 'mag', -getattr(source, 'flux', 0)))
                ref_sources = ref_sources[:settings.max_sources]
                anonymous_ref_stars = [
                    (source.x, source.y) for source in ref_sources
                ]
        elif isinstance(settings, AlignmentSettingsFeatures):
            # Extract algorithm-specific keywords
            if isinstance(settings, AlignmentSettingsFeaturesAKAZE):
                if settings.descriptor_type not in (
                        'KAZE', 'KAZE_UPRIGHT', 'MLDB', 'MLDB_UPRIGHT'):
                    raise ValueError(
                        f'Invalid descriptor type '
                        f'"{settings.descriptor_type}"')
                if settings.diffusivity not in (
                        'PM_G1', 'PM_G2', 'Weickert', 'Charbonnier'):
                    raise ValueError(
                        f'Invalid diffusivity "{settings.diffusivity}"')
                alignment_kwargs = {
                    'descriptor_type':
                        cv.AKAZE_DESCRIPTOR_KAZE
                        if settings.descriptor_type == 'KAZE' else
                        cv.AKAZE_DESCRIPTOR_KAZE_UPRIGHT
                        if settings.descriptor_type == 'KAZE_UPRIGHT' else
                        cv.AKAZE_DESCRIPTOR_MLDB
                        if settings.descriptor_type == 'MLDB' else
                        cv.AKAZE_DESCRIPTOR_MLDB_UPRIGHT,
                    'descriptor_size': settings.descriptor_size,
                    'descriptor_channels': settings.descriptor_channels,
                    'threshold': settings.threshold,
                    'nOctaves': settings.octaves,
                    'nOctaveLayers': settings.octave_layers,
                    'diffusivity':
                        cv.KAZE_DIFF_PM_G1
                        if settings.diffusivity == 'PM_G1' else
                        cv.KAZE_DIFF_PM_G2
                        if settings.diffusivity == 'PM_G2' else
                        cv.KAZE_DIFF_WEICKERT
                        if settings.diffusivity == 'Weickert' else
                        cv.KAZE_DIFF_CHARBONNIER,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesBRISK):
                alignment_kwargs = {
                    'thresh': settings.threshold,
                    'octaves': settings.octaves,
                    'patternScale': settings.pattern_scale,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesKAZE):
                if settings.diffusivity not in (
                        'PM_G1', 'PM_G2', 'Weickert', 'Charbonnier'):
                    raise ValueError(
                        f'Invalid diffusivity "{settings.diffusivity}"')
                alignment_kwargs = {
                    'extended': settings.extended,
                    'upright': settings.upright,
                    'threshold': settings.threshold,
                    'nOctaves': settings.octaves,
                    'nOctaveLayers': settings.octave_layers,
                    'diffusivity':
                        cv.KAZE_DIFF_PM_G1
                        if settings.diffusivity == 'PM_G1' else
                        cv.KAZE_DIFF_PM_G2
                        if settings.diffusivity == 'PM_G2' else
                        cv.KAZE_DIFF_WEICKERT
                        if settings.diffusivity == 'Weickert' else
                        cv.KAZE_DIFF_CHARBONNIER,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesORB):
                if settings.score_type not in ('Harris', 'fast'):
                    raise ValueError(
                        f'Invalid score type "{settings.score_type}"')
                alignment_kwargs = {
                    'nfeatures': settings.nfeatures,
                    'scaleFactor': settings.scale_factor,
                    'nlevels': settings.nlevels,
                    'edgeThreshold': settings.edge_threshold,
                    'firstLevel': settings.first_level,
                    'WTA_K': settings.wta_k,
                    'scoreType':
                        cv.ORB_HARRIS_SCORE
                        if settings.score_type == 'Harris' else
                        cv.ORB_FAST_SCORE,
                    'patchSize': settings.patch_size,
                    'fastThreshold': settings.fast_threshold,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesSIFT):
                alignment_kwargs = {
                    'nfeatures': settings.nfeatures,
                    'nOctaveLayers': settings.octave_layers,
                    'contrastThreshold': settings.contrast_threshold,
                    'edgeThreshold': settings.edge_threshold,
                    'sigma': settings.sigma,
                    'descriptorType':
                        cv.CV_32F if settings.descriptor_type == '32F' else
                        cv.CV_8U,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesSURF):
                alignment_kwargs = {
                    'hessianThreshold': settings.hessian_threshold,
                    'nOctaves': settings.octaves,
                    'nOctaveLayers': settings.octave_layers,
                    'extended': settings.extended,
                    'upright': settings.upright,
                }

        else:
            # WCS-based alignment
            ref_stars, anonymous_ref_stars = {}, []

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

        # Save and clear the original masks if auto-cropping is enabled
        masks = {}

        for i, file_id in enumerate(file_ids):
            try:
                # Load and transform the current image based on the chosen
                # mode
                data, hdr = get_data_file_data(self.user_id, file_id)

                if self.crop and isinstance(data, MaskedArray) and \
                        data.mask.any():
                    # Clear the original mask that would affect cropping
                    masks[file_id] = data.mask
                    data = data.filled(data.mean())

                if i != ref_image:
                    if isinstance(settings, AlignmentSettingsWCS):
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
                            prefilter=settings.prefilter,
                            enable_rot=settings.enable_rot,
                            enable_scale=settings.enable_scale,
                            enable_skew=settings.enable_skew)

                        hist_msg = 'WCS'

                    elif isinstance(settings, AlignmentSettingsSources):
                        if ref_stars:
                            # Extract current image sources that are also
                            # present in the reference image
                            img_sources = [
                                source for source in settings.sources
                                if getattr(source, 'file_id', None) == file_id]
                            img_stars = {
                                source.id: (source.x, source.y)
                                for source in img_sources
                                if getattr(source, 'id', None) is not None}
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
                                ref_height, prefilter=settings.prefilter,
                                enable_rot=settings.enable_rot,
                                enable_scale=settings.enable_scale,
                                enable_skew=settings.enable_skew)

                            nref = len(src_stars)
                            hist_msg = '{:d} star{}'.format(
                                nref, 's' if nref > 1 else '')

                        elif anonymous_ref_stars:
                            # Automatically match current image sources
                            # to reference image sources
                            img_sources = [
                                source for source in settings.sources
                                if getattr(source, 'file_id', None) == file_id]
                            if not img_sources:
                                raise ValueError('Missing alignment star(s)')

                            if len(anonymous_ref_stars) == 1 and \
                                    len(img_sources) == 1:
                                # Trivial case: 1-star match
                                src_stars = [
                                    (img_sources[0].x, img_sources[0].y)
                                ]
                                dst_stars = anonymous_ref_stars

                            else:
                                if len(img_sources) > settings.max_sources:
                                    img_sources.sort(
                                        key=lambda source: getattr(
                                            source, 'mag',
                                            -getattr(source, 'flux', 0)))
                                    img_sources = \
                                        img_sources[:settings.max_sources]
                                img_stars = [
                                    (source.x, source.y)
                                    for source in img_sources
                                ]
                                # Match two sets of points using pattern
                                # matching
                                src_stars, dst_stars = [], []
                                for k, l in enumerate(pattern_match(
                                        img_stars, anonymous_ref_stars,
                                        scale_invariant=settings
                                        .scale_invariant,
                                        eps=settings.match_tol,
                                        ksi=settings.min_edge,
                                        r_limit=settings.ratio_limit,
                                        confidence=settings.confidence)):
                                    if l >= 0:
                                        src_stars.append(img_stars[k])
                                        dst_stars.append(
                                            anonymous_ref_stars[l])
                                if not src_stars:
                                    raise ValueError('Pattern matching failed')

                            data = apply_transform_stars(
                                data, src_stars, dst_stars, ref_width,
                                ref_height, prefilter=settings.prefilter,
                                enable_rot=settings.enable_rot,
                                enable_scale=settings.enable_scale,
                                enable_skew=settings.enable_skew)

                            nref = len(src_stars)
                            hist_msg = '{:d} star{}{}'.format(
                                nref, 's' if nref > 1 else '',
                                '/pattern matching'
                                if len(img_sources) > 1 else '')

                        else:
                            # Should not happen
                            raise ValueError('No reference stars')

                    elif isinstance(settings, AlignmentSettingsFeatures):
                        data = apply_transform_features(
                            data, ref_data, settings.prefilter,
                            settings.enable_rot, settings.enable_scale,
                            settings.enable_skew, settings.algorithm,
                            settings.ratio_threshold, **alignment_kwargs)
                        hist_msg = f'{settings.algorithm} feature detection'

                    elif isinstance(settings, AlignmentSettingsPixels):
                        data = apply_transform_pixel(
                            data, ref_data, settings.prefilter,
                            settings.enable_rot, settings.enable_scale,
                            settings.enable_skew)
                        hist_msg = 'pixel matching'

                    else:
                        raise ValueError('Unknown alignment mode "{}"'
                                         .format(settings.mode))

                    hdr.add_history(
                        '[{}] Aligned by Afterglow using {} with respect '
                        'to data file {:d}'
                        .format(datetime.utcnow(), hist_msg, ref_file_id))

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
                        with get_data_file_db(self.user_id) as adb:
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
                    with get_data_file_db(self.user_id) as adb:
                        try:
                            save_data_file(
                                adb, get_root(self.user_id), file_id, data,
                                hdr)
                            adb.commit()
                        except Exception:
                            adb.rollback()
                            raise

                if i != ref_image or ref_file_id in self.file_ids:
                    self.result.file_ids.append(file_id)
            except Exception as e:
                self.add_error(e, {'file_id': file_ids[i]})
            finally:
                self.update_progress((i + 1)/len(file_ids)*100)

        # Optionally crop aligned files in place
        if self.crop:
            run_cropping_job(
                self, None, self.result.file_ids, inplace=True, masks=masks)
