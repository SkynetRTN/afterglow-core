"""
Afterglow Core: image alignment job plugin
"""

import gc
import time
from datetime import datetime

import numpy as np
from numpy.ma import MaskedArray
from numpy.linalg import inv
from scipy.sparse.csgraph import shortest_path
import scipy.ndimage as nd
from numba import njit
from marshmallow.fields import String, Integer, List, Nested
from astropy.wcs import WCS
import cv2 as cv
from flask import current_app

from skylib.combine.alignment import *
from skylib.combine.pattern_matching import pattern_match
from skylib.combine.cropping import get_auto_crop
from skylib.util.angle import angdist, average_radec
from skylib.util.fits import get_fits_fov

from ...database import db
from ...models import Job, JobResult, SourceExtractionData
from ...schemas import AfterglowSchema, Boolean, Float, NestedPoly
from ...errors import AfterglowError, ValidationError
from ..data_files import (
    create_data_file, get_data_file, get_data_file_data, get_data_file_fits, get_root, save_data_file)
from .source_extraction_job import SourceExtractionSettings, run_source_extraction_job
from .cropping_job import run_cropping_job


__all__ = ['AlignmentJob']


MAX_MOSAIC_SIZE = 16384


class AlignmentSettings(AfterglowSchema):
    __polymorphic_on__ = 'mode'

    mode: str = String(dump_default='WCS', load_default='WCS')
    ref_image: str | None = String(dump_default='central', allow_none=True)
    mosaic_search_radius: float = Float(dump_default=1)
    enable_rot: bool = Boolean(dump_default=True)
    enable_scale: bool = Boolean(dump_default=True)
    enable_skew: bool = Boolean(dump_default=True)
    ignore_overlap: bool = Boolean(dump_default=True)
    global_contrast: bool = Boolean(dump_default=True)
    percentile_min: float = Float(dump_default=10)
    percentile_max: float = Float(dump_default=99)
    detect_edges: bool = Boolean(dump_default=False)


class AlignmentSettingsWCS(AlignmentSettings):
    mode = 'WCS'
    wcs_grid_points: int = Integer(dump_default=100)


class AlignmentSettingsSources(AlignmentSettings):
    scale_invariant: bool = Boolean(dump_default=False)
    match_tol: float = Float(dump_default=0.002)
    min_edge: float = Float(dump_default=0.003)
    ratio_limit: float = Float(dump_default=10)
    confidence: float = Float(dump_default=0.15)


class AlignmentSettingsSourcesManual(AlignmentSettingsSources):
    mode = 'sources_manual'
    max_sources: int = Integer(dump_default=100)
    sources: list[SourceExtractionData] = List(Nested(SourceExtractionData), dump_default=[])


class AlignmentSettingsSourcesAuto(AlignmentSettingsSources):
    mode = 'sources_auto'
    source_extraction_settings: SourceExtractionSettings | None = Nested(
        SourceExtractionSettings, allow_none=True, dump_default=None)


class AlignmentSettingsFeatures(AlignmentSettings):
    __polymorphic_on__ = 'algorithm'

    mode = 'features'

    algorithm: str = String(dump_default='AKAZE', load_default='AKAZE')
    ratio_threshold: float = Float(dump_default=0.4)
    downsample: int = Integer(dump_default=2)


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


class AlignmentJobResult(JobResult):
    file_ids: list[int] = List(Integer(), dump_default=[])


class AlignmentJob(Job):
    """
    Image alignment job
    """
    type = 'alignment'
    description = 'Align Images'

    result: AlignmentJobResult = Nested(AlignmentJobResult, dump_default={})
    file_ids: list[int] = List(Integer(), dump_default=[])
    settings: AlignmentSettings = NestedPoly(AlignmentSettings, dump_default={})
    inplace: bool = Boolean(dump_default=False)
    crop: bool = Boolean(dump_default=False)

    def run(self):
        settings = self.settings

        # Load data files
        file_ids = list(self.file_ids)
        if not file_ids:
            return

        try:
            # Get reference image index and the corresponding data file ID
            if settings.ref_image is None:
                ref_image = None
            elif settings.ref_image == 'first':
                ref_image = 0
            elif settings.ref_image == 'last':
                ref_image = len(file_ids) - 1
            elif settings.ref_image == 'central':
                ref_image = len(file_ids)//2
            elif settings.ref_image.strip().startswith('#'):
                # 0-based index in file_ids
                ref_image = int(settings.ref_image.strip()[1:])
                if not 0 <= ref_image < len(file_ids):
                    raise ValidationError('settings.ref_image', 'Reference image index out of range', 422)
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
                'Reference image must be "first", "last", "central", or data file ID, or #file_no', 422)
        if ref_image is None:
            ref_file_id = None
        else:
            ref_file_id = file_ids[ref_image]

        alignment_kwargs = {}

        if isinstance(settings, AlignmentSettingsSourcesManual):
            # Check that all sources have file IDs
            if not settings.sources:
                raise ValueError('Missing sources for manual alignment')
            if any(not hasattr(source, 'file_id') for source in settings.sources):
                raise ValueError('Missing data file ID for at least one source')
        elif isinstance(settings, AlignmentSettingsFeatures):
            # Extract algorithm-specific keywords
            alignment_kwargs['downsample'] = settings.downsample
            if isinstance(settings, AlignmentSettingsFeaturesAKAZE):
                if settings.descriptor_type not in ('KAZE', 'KAZE_UPRIGHT', 'MLDB', 'MLDB_UPRIGHT'):
                    raise ValueError(f'Invalid descriptor type "{settings.descriptor_type}"')
                if settings.diffusivity not in ('PM_G1', 'PM_G2', 'Weickert', 'Charbonnier'):
                    raise ValueError(f'Invalid diffusivity "{settings.diffusivity}"')
                alignment_kwargs = {
                    'descriptor_type':
                        cv.AKAZE_DESCRIPTOR_KAZE if settings.descriptor_type == 'KAZE' else
                        cv.AKAZE_DESCRIPTOR_KAZE_UPRIGHT if settings.descriptor_type == 'KAZE_UPRIGHT' else
                        cv.AKAZE_DESCRIPTOR_MLDB if settings.descriptor_type == 'MLDB' else
                        cv.AKAZE_DESCRIPTOR_MLDB_UPRIGHT,
                    'descriptor_size': settings.descriptor_size,
                    'descriptor_channels': settings.descriptor_channels,
                    'threshold': settings.threshold,
                    'nOctaves': settings.octaves,
                    'nOctaveLayers': settings.octave_layers,
                    'diffusivity':
                        cv.KAZE_DIFF_PM_G1 if settings.diffusivity == 'PM_G1' else
                        cv.KAZE_DIFF_PM_G2 if settings.diffusivity == 'PM_G2' else
                        cv.KAZE_DIFF_WEICKERT if settings.diffusivity == 'Weickert' else
                        cv.KAZE_DIFF_CHARBONNIER,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesBRISK):
                alignment_kwargs = {
                    'thresh': settings.threshold,
                    'octaves': settings.octaves,
                    'patternScale': settings.pattern_scale,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesKAZE):
                if settings.diffusivity not in ('PM_G1', 'PM_G2', 'Weickert', 'Charbonnier'):
                    raise ValueError(f'Invalid diffusivity "{settings.diffusivity}"')
                alignment_kwargs = {
                    'extended': settings.extended,
                    'upright': settings.upright,
                    'threshold': settings.threshold,
                    'nOctaves': settings.octaves,
                    'nOctaveLayers': settings.octave_layers,
                    'diffusivity':
                        cv.KAZE_DIFF_PM_G1 if settings.diffusivity == 'PM_G1' else
                        cv.KAZE_DIFF_PM_G2 if settings.diffusivity == 'PM_G2' else
                        cv.KAZE_DIFF_WEICKERT if settings.diffusivity == 'Weickert' else
                        cv.KAZE_DIFF_CHARBONNIER,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesORB):
                if settings.score_type not in ('Harris', 'fast'):
                    raise ValueError(f'Invalid score type "{settings.score_type}"')
                alignment_kwargs = {
                    'nfeatures': settings.nfeatures,
                    'scaleFactor': settings.scale_factor,
                    'nlevels': settings.nlevels,
                    'edgeThreshold': settings.edge_threshold,
                    'firstLevel': settings.first_level,
                    'WTA_K': settings.wta_k,
                    'scoreType': cv.ORB_HARRIS_SCORE if settings.score_type == 'Harris' else cv.ORB_FAST_SCORE,
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
                    'descriptorType': cv.CV_32F if settings.descriptor_type == '32F' else cv.CV_8U,
                }
            elif isinstance(settings, AlignmentSettingsFeaturesSURF):
                alignment_kwargs = {
                    'hessianThreshold': settings.hessian_threshold,
                    'nOctaves': settings.octaves,
                    'nOctaveLayers': settings.octave_layers,
                    'extended': settings.extended,
                    'upright': settings.upright,
                }

        # Handle progress: at least 2 stages (calculating and applying transforms)
        total_stages = 2
        if self.crop:
            # Post-cropping
            total_stages += 1
        if ref_file_id is None:
            # Pre-cropping
            total_stages += 1
            if settings.global_contrast:
                # Calculation of global clip_min, clip_max
                total_stages += 1
        stage = 0

        wcs_cache, data_cache = {}, {}
        transforms, history = {}, {}
        mosaics = []

        if ref_file_id is not None:
            # Calculate transforms for all non-reference images
            for i, file_id in enumerate(file_ids):
                if i == ref_image:
                    continue
                try:
                    transforms[file_id], history[file_id] = get_transform(
                        self, alignment_kwargs, file_id, ref_file_id, wcs_cache, data_cache)
                except Exception as e:
                    self.add_error(e, {'file_id': file_ids[i]})
                finally:
                    self.update_progress((i + 1)/len(file_ids)*100, stage, total_stages)

            stage += 1

            with get_data_file_fits(self.user_id, ref_file_id) as f:
                hdr = f[0].header
            ref_width, ref_height = hdr['NAXIS1'], hdr['NAXIS2']
            try:
                ref_wcs = get_wcs(self.user_id, ref_file_id, wcs_cache)
            except ValueError:
                ref_wcs = None

            # Reference image parameters are the same for all non-ref images
            ref_heights = {file_id: ref_height for file_id in file_ids if file_id != ref_file_id}
            ref_widths = {file_id: ref_width for file_id in file_ids if file_id != ref_file_id}
            ref_wcss = {file_id: ref_wcs for file_id in file_ids if file_id != ref_file_id}

        else:  # Mosaicing mode
            # Crop images to prevent memory overflow if realigning
            t0 = time.time()
            fovs, shapes, filters = {}, {}, {}
            all_data = {}
            for i, file_id in enumerate(file_ids):
                with get_data_file_fits(self.user_id, file_id) as f:
                    hdr = f[0].header
                    data = f[0].data
                    del f[0].data
                mask = np.isnan(data)
                if mask.any():
                    left, right, bottom, top = get_auto_crop(mask)
                    if any([left, right, bottom, top]) and left + right < data.shape[1] and \
                            bottom + top < data.shape[0]:
                        data = data[bottom:data.shape[0]-top, left:data.shape[1]-right]
                        hdr['NAXIS2'], hdr['NAXIS1'] = data.shape
                        if left:
                            try:
                                hdr['CRPIX1'] -= left
                            except TypeError:
                                try:
                                    hdr['CRPIX1'] = float(hdr['CRPIX1']) - left
                                except (TypeError, ValueError):
                                    pass
                            except (KeyError, ValueError):
                                pass
                        if bottom:
                            try:
                                hdr['CRPIX2'] -= bottom
                            except TypeError:
                                try:
                                    hdr['CRPIX2'] = float(hdr['CRPIX2']) - bottom
                                except (TypeError, ValueError):
                                    pass
                            except (KeyError, ValueError):
                                pass
                        try:
                            # Overwrite the original data file
                            save_data_file(get_root(self.user_id), file_id, data, hdr)
                            db.session.commit()
                        except Exception:
                            db.session.rollback()
                            raise

                # Cache tile geometry and other info
                fovs[file_id] = get_fits_fov(hdr)
                shapes[file_id] = data.shape
                # noinspection PyBroadException
                try:
                    wcs_cache[file_id] = WCS(hdr)
                except Exception:
                    wcs_cache[file_id] = None
                flt = filters[file_id] = hdr.get('FILTER', '')

                if settings.global_contrast:
                    if settings.detect_edges:
                        data = np.hypot(nd.sobel(data, 0, mode='nearest'), nd.sobel(data, 1, mode='nearest'))
                    all_data.setdefault(flt, []).append(data.ravel())

                del data
                self.update_progress((i + 1)/len(file_ids)*100, stage, total_stages)
            stage += 1
            current_app.logger.info('PROFILE preprocess %.3g', time.time() - t0)

            if all_data:
                # Calculate global contrast (separately for each filter), which allows caching features
                t0 = time.time()
                clip = {}
                for i, (flt, all_data_for_filter) in enumerate(all_data.items()):
                    clip_min, clip_max = calc_contrast(
                        np.concatenate(all_data_for_filter), settings.percentile_min, settings.percentile_max)
                    del all_data_for_filter
                    for file_id in file_ids:
                        if filters[file_id] == flt:
                            clip[file_id] = clip_min, clip_max
                    self.update_progress((i + 1)/len(all_data)*100, stage, total_stages)
                stage += 1
                del all_data
                current_app.logger.info('PROFILE global_contrast %.3g', time.time() - t0)
            else:
                # Calculate the contrast for each pair of tiles
                clip = {file_id: (None, None) for file_id in file_ids}

            # Find all possible pairwise transformations
            t0 = time.time()
            gcd_time = get_transform_time = update_progress_time = 0
            rel_transforms, weights = {}, {}
            n = len(file_ids)
            total_pairs = n*(n - 1)//2
            max_r = settings.mosaic_search_radius
            k = 0
            for i, file_id in enumerate(file_ids[:-1]):
                ra0, dec0, r0, _, w0, h0 = fovs[file_id]
                for other_file_id in file_ids[i + 1:]:
                    # Calculate the GCD between tile centers
                    t00 = time.time()
                    other_ra0, other_dec0, other_r0, _, w, h = fovs[other_file_id]
                    if all(x is not None for x in (ra0, dec0, other_ra0, other_dec0)):
                        gcd = angdist(ra0, dec0, other_ra0, other_dec0)
                        if r0 is None or other_r0 is None:
                            max_gcd = None
                        else:
                            max_gcd = (r0 + other_r0)*max_r
                    else:
                        gcd = max_gcd = None
                    gcd_time += time.time() - t00

                    # Ignore faraway tiles unless WCS mode or FOV unknown
                    if isinstance(settings, AlignmentSettingsWCS) or max_gcd is None or gcd < max_gcd:
                        # Calculate pairwise transform
                        # noinspection PyBroadException
                        try:
                            t00 = time.time()
                            rel_transforms[file_id, other_file_id], history[file_id] = get_transform(
                                self, alignment_kwargs, other_file_id, file_id, wcs_cache, data_cache,
                                clip[file_id][0], clip[file_id][1], clip[other_file_id][0], clip[other_file_id][1])
                            get_transform_time += time.time() - t00
                        except Exception:
                            # No match found
                            pass
                        else:
                            # Add inverse transformations
                            mat, offset = rel_transforms[file_id, other_file_id]
                            if mat is None:
                                inv_mat = None
                                inv_offset = -offset
                            else:
                                inv_mat = inv(mat)
                                inv_offset = -np.dot(inv_mat, offset)
                            rel_transforms[other_file_id, file_id] = (inv_mat, inv_offset)

                            # Calculate graph edge weights
                            if settings.ignore_overlap:
                                # Assign unit lengths to all edges
                                weights[file_id, other_file_id] = 1
                            elif isinstance(settings, AlignmentSettingsWCS):
                                # For WCS-based alignment, tiles don't necessarily overlap. Use GCD as the measure of
                                # path length on the graph.
                                if gcd is not None:
                                    weights[file_id, other_file_id] = gcd
                                else:
                                    # No RA/Dec info in header, assume constant weight
                                    weights[file_id, other_file_id] = 1
                            else:
                                # For other alignment modes, the distance is the inverse square of the normalized tile
                                # overlap area. Tile pairs with no overlap are considered false matches.
                                y, x = np.indices((h, w)).astype(float)
                                y, x = y.ravel(), x.ravel()
                                y += inv_offset[0]
                                x += inv_offset[1]
                                if inv_mat is not None:
                                    y, x = np.dot(inv_mat, [y, x])
                                overlap = ((x >= 0) & (x < w0) & (y >= 0) & (y < h0)).sum()/max(w*h, w0*h0)
                                if overlap:
                                    weights[file_id, other_file_id] = 1/overlap**2
                                else:
                                    del rel_transforms[file_id, other_file_id]
                                    del rel_transforms[other_file_id, file_id]

                            # Undirected graph
                            try:
                                weights[other_file_id, file_id] = weights[file_id, other_file_id]
                            except KeyError:
                                # Match discarded because of no overlap
                                pass
                    k += 1
                    if not k % 10 or k == total_pairs:
                        t00 = time.time()
                        self.update_progress(k/total_pairs*100, stage, total_stages)
                        update_progress_time += time.time() - t00

            stage += 1
            current_app.logger.info('PROFILE gcd %.3g', gcd_time)
            current_app.logger.info('PROFILE get_transform %.3g', get_transform_time)
            current_app.logger.info('PROFILE update_progress %.3g', update_progress_time)
            current_app.logger.info('PROFILE get_pairwise_transforms %.3g', time.time() - t0)

            # Include each image in one of the sets of connected images ("mosaics") if it has at least one match
            ref_widths, ref_heights, ref_wcss = {}, {}, {}
            for file_id in file_ids:
                matching_file_ids = {file_id2 for file_id1, file_id2 in rel_transforms.keys() if file_id1 == file_id}
                if not matching_file_ids:
                    # Isolated image; skip
                    continue
                # Find all existing mosaics containing at least one of the matching images
                matching_mosaics = []
                for mosaic in mosaics:
                    if mosaic & matching_file_ids:
                        # Include image in the existing mosaic
                        matching_mosaics.append(mosaic)
                if matching_mosaics:
                    if len(matching_mosaics) > 1:
                        # Image has a match in multiple mosaics; join them
                        new_mosaics = [set(sum([list(mosaic) for mosaic in matching_mosaics], []))]
                        new_mosaics[0].add(file_id)
                        for mosaic in mosaics:
                            if mosaic not in matching_mosaics:
                                new_mosaics.append(mosaic)
                        mosaics = new_mosaics
                    else:
                        matching_mosaics[0].add(file_id)
                else:
                    # Start a new mosaic
                    mosaics.append({file_id})
            if not mosaics:
                raise ValueError('Cannot find a match between any images')

            # Process each mosaic separately
            for mosaic in mosaics:
                t0 = time.time()
                # Put the tile closest to the average mosaic RA/Dec first; this will be the reference tile
                mosaic = list(mosaic)
                ra0, dec0 = average_radec(np.array([fovs[file_id][:2] for file_id in mosaic]))
                i = np.argmin([angdist(ra0, dec0, *fovs[file_id][:2]) for file_id in mosaic])
                if i:
                    mosaic = [mosaic[i]] + mosaic[:i] + mosaic[i+1:]

                # Based on the existing pairwise transformations, build an undirected weighted graph with vertices
                # representing tile centers and edge weights defined by great circle distances or overlap areas
                n = len(mosaic)
                graph = np.full((n, n), np.nan, np.float64)
                for idx, d in weights.items():
                    try:
                        i, j = mosaic.index(idx[0]), mosaic.index(idx[1])
                    except ValueError:
                        # Different mosaic
                        pass
                    else:
                        graph[i, j] = d
                pred = shortest_path(graph, return_predecessors=True)[1]

                # Establish the global reference frame based on the first image
                ref_height, ref_width = shapes[mosaic[0]]
                transforms[mosaic[0]] = None, np.zeros(2)

                # Update the mosaic image shape and transformations by adding each subsequent image
                for i in range(1, n):
                    file_id = mosaic[i]
                    mat, offset = transforms[mosaic[0]]

                    # Reconstruct the shortest path from the first tile in the graph and project the current image
                    # coordinates onto the global reference frame by chaining pairwise transforms along the path
                    j = 0
                    while True:
                        j1 = pred[i, j]

                        # Get the transform from j-th to the intermediate j1-th tile
                        mat1, offset1 = rel_transforms[mosaic[j1], mosaic[j]]

                        # Chain the transform with the already established transform from 1st to j-th tile
                        if mat is None:
                            mat = mat1
                            offset = offset + offset1
                        else:
                            if mat1 is not None:
                                mat = np.dot(mat, mat1)
                            offset = offset + np.dot(mat, offset1)

                        if j1 == i:
                            # Reached the current tile
                            break

                        j = j1

                    # Got new transform; check that the transformed tile fits within the current global mosaic frame
                    transforms[file_id] = mat, offset
                    dy, dx = offset
                    y, x = np.indices(shapes[file_id])
                    if mat is None:
                        x = x + dx  # adding float to int
                        y = y + dy
                    else:
                        y, x = np.tensordot(mat, [y, x], 1) + [[[dy]], [[dx]]]
                    xmin, xmax = int(np.floor(x.min())), int(np.ceil(x.max()))
                    ymin, ymax = int(np.floor(y.min())), int(np.ceil(y.max()))
                    if xmin < 0:
                        # Shift all existing transformations and extend the mosaic to the left
                        for j in range(i + 1):
                            transforms[mosaic[j]][1][1] -= xmin
                        ref_width -= xmin
                    if xmax > ref_width - 1:
                        # Extend the mosaic to the right
                        ref_width = xmax + 1
                    if ymin < 0:
                        # Shift all existing transformations and extend the mosaic to the bottom
                        for j in range(i + 1):
                            transforms[mosaic[j]][1][0] -= ymin
                        ref_height -= ymin
                    if ymax > ref_height - 1:
                        # Extend the mosaic to the top
                        ref_height = ymax + 1

                if ref_width*ref_height > MAX_MOSAIC_SIZE**2:
                    raise ValueError(
                        'Mosaic size ({0}x{1}) exceeds the maximum ({2}x{2})'
                        .format(ref_width, ref_height, MAX_MOSAIC_SIZE))

                # Invert all transforms since apply_transform() assumes the backward direction
                for file_id in mosaic:
                    mat, offset = transforms[file_id]
                    if mat is None:
                        offset = -offset
                    else:
                        mat = inv(mat)
                        offset = -np.dot(mat, offset)
                    transforms[file_id] = mat, offset

                # Set the reference image sizes for all images in the mosaic
                for file_id in mosaic:
                    ref_widths[file_id] = ref_width
                    ref_heights[file_id] = ref_height

                # Calculate the mosaic WCS from any of the available individual image WCSs
                for file_id in mosaic:
                    wcs = wcs_cache.get(file_id)
                    if wcs is not None:
                        for other_file_id in mosaic:
                            ref_wcss[other_file_id] = wcs
                        break

                current_app.logger.info('PROFILE get_abs_transforms %.3g', time.time() - t0)

        del wcs_cache, data_cache
        gc.collect()

        # Save and later temporarily clear the original masks if auto-cropping is enabled; the masks will be restored by
        # the cropping job
        masks = {}

        # In mosaicing mode, we'll potentially need to run multiple cropping jobs
        cropping_jobs = [[] for _ in range(len(mosaics))] if mosaics \
            else [[ref_file_id]] if ref_file_id is not None else [[]]

        # Apply transforms
        t0 = time.time()
        for i, file_id in enumerate(file_ids):
            try:
                try:
                    mat, offset = transforms[file_id]
                except KeyError:
                    if file_id != ref_file_id:
                        raise RuntimeError('Cannot align image')
                    continue

                data, hdr = get_data_file_data(self.user_id, file_id)

                overwrite_ref = self.crop and isinstance(data, MaskedArray) and data.mask.any()

                data = apply_transform(data, mat, offset, ref_widths[file_id], ref_heights[file_id])

                if overwrite_ref:
                    # Save and clear the mask before auto-cropping
                    masks[file_id] = data.mask
                    data = data.filled(data.mean())

                try:
                    hdr.add_history(
                        '[{}] {} by Afterglow using {}{}'.format(
                            datetime.utcnow(),
                            'Aligned' if ref_file_id is not None else 'Aligned for mosaicing',
                            history[file_id],
                            ' with respect to data file {:d}'.format(ref_file_id) if ref_file_id is not None else ''))
                except KeyError:
                    pass

                # Copy WCS from reference image if any
                if ref_wcss.get(file_id) is not None:
                    # Preserve epoch of observation
                    orig_kw = {
                        name: (hdr[name], hdr.comments[name]) if hdr.comments[name] else hdr[name]
                        for name in ('DATE-OBS', 'MJD-OBS') if name in hdr
                    }

                    # Remove the possible alternative WCS representations to avoid WCS compatibility issues and make
                    # the WCS consistent
                    for name in (
                            'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2',
                            'PC1_1', 'PC1_2', 'PC2_1', 'PC2_2',
                            'CDELT1', 'CDELT2', 'CROTA1', 'CROTA2'):
                        try:
                            del hdr[name]
                        except KeyError:
                            pass

                    hdr.update(ref_wcss[file_id].to_header(relax=True))
                    for name, val in orig_kw.items():
                        hdr[name] = val

                # Store only non-masked area
                origin = size = None
                if mosaics and isinstance(data, np.ma.MaskedArray) and data.mask is not False and data.mask.any():
                    left, right, bottom, top = get_auto_crop(data.mask)
                    if any([left, right, bottom, top]) and left + right < data.shape[1] and \
                            bottom + top < data.shape[0]:
                        origin = left, bottom
                        size = tuple(data.shape[::-1])
                        data = data[bottom:data.shape[0]-top, left:data.shape[1]-right]
                        if not data.mask.any():
                            data = data.data

                new_file_id = file_id
                if not self.inplace:
                    # Don't create a new data file for reference image that was not listed in file_ids but was instead
                    # passed in settings.ref_image
                    if i != ref_image or overwrite_ref or ref_file_id in self.file_ids:
                        try:
                            hdr.add_history(
                                'Original data file: {}'.format(get_data_file(self.user_id, file_id).name or file_id))
                            new_file_id = create_data_file(
                                self.user_id, None, get_root(self.user_id), data, hdr, origin=origin, size=size,
                                duplicates='append', session_id=self.session_id).id
                            db.session.commit()
                        except Exception:
                            db.session.rollback()
                            raise
                elif i != ref_image or overwrite_ref:
                    try:
                        save_data_file(get_root(self.user_id), file_id, data, hdr, origin=origin, size=size)
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                        raise

                if i != ref_image or overwrite_ref or ref_file_id in self.file_ids:
                    self.result.file_ids.append(new_file_id)

                if mosaics:
                    for j in range(len(mosaics)):
                        if file_id in mosaics[j]:
                            cropping_jobs[j].append(new_file_id)
                            break
                else:
                    cropping_jobs[0].append(new_file_id)

            except Exception as e:
                self.add_error(e, {'file_id': file_id})
            finally:
                self.update_progress((i + 1)/len(file_ids)*100, stage, total_stages)

        stage += 1
        current_app.logger.info('PROFILE create_large_tiles %.3g', time.time() - t0)

        # Optionally crop aligned files in place
        if self.crop:
            for file_ids in cropping_jobs:
                run_cropping_job(
                    self, None, file_ids, inplace=True, masks=masks, stage=stage, total_stages=total_stages)


def get_wcs(user_id: int | None, file_id: int, wcs_cache: dict[int, WCS]) -> WCS:
    try:
        wcs = wcs_cache[file_id]
    except KeyError:
        # noinspection PyBroadException
        try:
            with get_data_file_fits(user_id, file_id) as fits:
                wcs = WCS(fits[0].header)
            if not wcs.has_celestial:
                wcs = None
        except Exception:
            wcs = None
        wcs_cache[file_id] = wcs
    if wcs is None:
        raise ValueError('Missing WCS')
    return wcs


def get_source_xy(source: SourceExtractionData, user_id: int | None, file_id: int, wcs_cache: dict[int, WCS]) \
        -> tuple[float, float]:
    x, y = getattr(source, 'x', None), getattr(source, 'y', None)
    if x is None or y is None:
        wcs = get_wcs(user_id, file_id, wcs_cache)
        x, y = wcs.all_world2pix(source.ra_hours*15, source.dec_degs, 1, quiet=True)
    return x, y


@njit(cache=True)
def calc_contrast(data: np.ndarray, percentile_min: float, percentile_max: float) -> tuple[float, float]:
    have_nans = False
    for x in data:
        if np.isnan(x):
            have_nans = True
            break

    if percentile_min <= 0:
        if have_nans:
            clip_min = np.nanmin(data)
        else:
            clip_min = data.min()
        if percentile_max >= 100:
            if have_nans:
                clip_max = np.nanmax(data)
            else:
                clip_max = data.max()
        elif have_nans:
            clip_max = np.nanpercentile(data, percentile_max)
        else:
            clip_max = np.percentile(data, percentile_max)
    elif percentile_max >= 100:
        if have_nans:
            clip_min, clip_max = np.nanpercentile(data, percentile_min), np.nanmax(data)
        else:
            clip_min, clip_max = np.percentile(data, percentile_min), data.max()
    elif have_nans:
        clip_min, clip_max = np.nanpercentile(data, [percentile_min, percentile_max])
    else:
        clip_min, clip_max = np.percentile(data, [percentile_min, percentile_max])
    return clip_min, clip_max


def get_transform(job: AlignmentJob, alignment_kwargs: dict[str, object], file_id: int, ref_file_id: int,
                  wcs_cache: dict[int, WCS], data_cache: dict[int, object], clip_min1: float | None = None,
                  clip_max1: float | None = None, clip_min2: float | None = None, clip_max2: float | None = None) \
        -> tuple[tuple[np.ndarray | None, np.ndarray], str]:
    settings = job.settings
    user_id = job.user_id

    if isinstance(settings, AlignmentSettingsWCS):
        # Extract current and reference image WCS
        wcs = get_wcs(user_id, file_id, wcs_cache)
        try:
            ref_wcs = get_wcs(user_id, ref_file_id, wcs_cache)
        except ValueError:
            raise ValueError('Reference image has no WCS')

        return get_transform_wcs(
            wcs, ref_wcs,
            grid_points=settings.wcs_grid_points,
            enable_rot=settings.enable_rot,
            enable_scale=settings.enable_scale,
            enable_skew=settings.enable_skew), 'WCS'

    if isinstance(settings, AlignmentSettingsSources):
        # Extract alignment stars for reference image
        try:
            ref_stars, anonymous_ref_stars = data_cache[ref_file_id]
        except KeyError:
            if isinstance(settings, AlignmentSettingsSourcesManual):
                ref_sources = [source for source in settings.sources if getattr(source, 'file_id', None) == ref_file_id]
                if not ref_sources:
                    raise ValueError('Missing alignment stars for reference image')
                ref_stars = {
                    source.id: get_source_xy(source, user_id, ref_file_id, wcs_cache)
                    for source in ref_sources if getattr(source, 'id', None) is not None
                }
                anonymous_ref_stars = [
                    get_source_xy(source, user_id, ref_file_id, wcs_cache)
                    for source in ref_sources if getattr(source, 'id', None) is None
                ]
                if ref_stars and anonymous_ref_stars:
                    # Cannot mix sources with and without ID
                    raise ValueError('All or none of the reference image source must have source ID')
                if len(anonymous_ref_stars) > settings.max_sources:
                    # Too many stars for pattern matching; sort by brightness and use at most max_sources stars
                    ref_sources.sort(key=lambda source: getattr(source, 'mag', -getattr(source, 'flux', 0)))
                    ref_sources = ref_sources[:settings.max_sources]
                    anonymous_ref_stars = [
                        get_source_xy(source, user_id, ref_file_id, wcs_cache) for source in ref_sources
                    ]
            elif isinstance(settings, AlignmentSettingsSourcesAuto):
                ref_sources = run_source_extraction_job(
                    job, settings.source_extraction_settings, [ref_file_id], total_stages=0)[0]
                if not ref_sources:
                    raise ValueError('Cannot extract any alignment stars from reference image')
                ref_stars = {}
                anonymous_ref_stars = [(source.x, source.y) for source in ref_sources]
            else:
                raise ValueError('Unknown alignment mode "{}"'.format(settings.mode))
            data_cache[ref_file_id] = ref_stars, anonymous_ref_stars

        if ref_stars:
            # Explicit matching by source IDs: extract current image sources that are also present in the reference
            # image
            img_sources = [source for source in settings.sources if getattr(source, 'file_id', None) == file_id]
            img_stars = {
                source.id: get_source_xy(source, user_id, file_id, wcs_cache)
                for source in img_sources if getattr(source, 'id', None) is not None}
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
            nref = len(src_stars)
            return get_transform_stars(
                src_stars, dst_stars,
                enable_rot=settings.enable_rot,
                enable_scale=settings.enable_scale,
                enable_skew=settings.enable_skew), '{:d} star{}'.format(nref, 's' if nref > 1 else '')

        # Automatically match current image sources to reference image sources
        if isinstance(settings, AlignmentSettingsSourcesManual):
            img_sources = [source for source in settings.sources if getattr(source, 'file_id', None) == file_id]
            if not img_sources:
                raise ValueError('Missing alignment star(s)')
            if len(img_sources) > settings.max_sources:
                img_sources.sort(key=lambda source: getattr(source, 'mag', -getattr(source, 'flux', 0)))
                img_sources = img_sources[:settings.max_sources]
        elif isinstance(settings, AlignmentSettingsSourcesAuto):
            img_sources = run_source_extraction_job(
                job, settings.source_extraction_settings, [file_id], total_stages=0)[0]
            if not img_sources:
                raise ValueError('Cannot extract any alignment stars')
        else:
            raise ValueError('Unknown alignment mode "{}"'.format(settings.mode))

        if len(anonymous_ref_stars) == 1 and len(img_sources) == 1:
            # Trivial case: 1-star match
            src_stars = [(img_sources[0].x, img_sources[0].y)]
            dst_stars = anonymous_ref_stars
        else:
            img_stars = [get_source_xy(source, user_id, file_id, wcs_cache) for source in img_sources]
            # Match two sets of points using pattern matching
            src_stars, dst_stars = [], []
            for k, l in enumerate(pattern_match(
                    img_stars, anonymous_ref_stars,
                    scale_invariant=settings.scale_invariant,
                    eps=settings.match_tol,
                    ksi=settings.min_edge,
                    r_limit=settings.ratio_limit,
                    confidence=settings.confidence)):
                if l >= 0:
                    src_stars.append(img_stars[k])
                    dst_stars.append(anonymous_ref_stars[l])
            if not src_stars:
                raise ValueError('Pattern matching failed')

        nref = len(src_stars)
        return (get_transform_stars(
            src_stars, dst_stars,
            enable_rot=settings.enable_rot,
            enable_scale=settings.enable_scale,
            enable_skew=settings.enable_skew),
            '{:d} star{}{}'
            .format(nref, 's' if nref > 1 else '', '/pattern matching' if len(img_sources) > 1 else ''))

    if isinstance(settings, AlignmentSettingsFeatures):
        # Try getting features from cache (global contrast only)
        try:
            kp1, des1 = data_cache[file_id]
        except KeyError:
            kp1 = des1 = None
        try:
            kp2, des2 = data_cache[ref_file_id]
        except KeyError:
            kp2 = des2 = None
        if any(item is None for item in (kp1, des1, kp2, des2)):
            # Extract missing features
            feature_kwargs = dict(alignment_kwargs)
            feature_kwargs.update(dict(
                algorithm=settings.algorithm,
                downsample=settings.downsample,
            ))
            if settings.global_contrast:
                # clip_min and clip_max are already calculated; extract features for those images in the pair that
                # are missing from the cache
                feature_kwargs['detect_edges'] = settings.detect_edges
                if any(item is None for item in (kp1, des1)):
                    with get_data_file_fits(user_id, file_id) as fits:
                        data1 = fits[0].data
                        del fits[0].data
                    data_cache[file_id] = kp1, des1 = get_image_features(
                        data1, clip_min=clip_min1, clip_max=clip_max1, **feature_kwargs)
                    del data1
                if any(item is None for item in (kp2, des2)):
                    with get_data_file_fits(user_id, ref_file_id) as fits:
                        data2 = fits[0].data
                        del fits[0].data
                    data_cache[ref_file_id] = kp2, des2 = get_image_features(
                        data2, clip_min=clip_min2, clip_max=clip_max2, **feature_kwargs)
                    del data2
            else:
                # Make sure that both images are on the same contrast scale
                with get_data_file_fits(user_id, file_id) as fits:
                    data1 = fits[0].data
                    del fits[0].data
                with get_data_file_fits(user_id, ref_file_id) as fits:
                    data2 = fits[0].data
                    del fits[0].data
                if settings.detect_edges:
                    data1 = np.hypot(nd.sobel(data1, 0, mode='nearest'), nd.sobel(data1, 1, mode='nearest'))
                    data2 = np.hypot(nd.sobel(data2, 0, mode='nearest'), nd.sobel(data2, 1, mode='nearest'))
                if any(item is None for item in (clip_min1, clip_max1, clip_min2, clip_max2)):
                    clip_min1, clip_max1 = clip_min2, clip_max2 = calc_contrast(
                        np.concatenate([data1.ravel(), data2.ravel()]),
                        settings.percentile_min, settings.percentile_max)
                feature_kwargs['detect_edges'] = False
                kp1, des1 = get_image_features(data1, clip_min=clip_min1, clip_max=clip_max1, **feature_kwargs)
                kp2, des2 = get_image_features(data2, clip_min=clip_min2, clip_max=clip_max2, **feature_kwargs)

        # Compute the transformation based on matching features
        res = get_transform_features(
            kp1, des1, kp2, des2,
            enable_rot=settings.enable_rot,
            enable_scale=settings.enable_scale,
            enable_skew=settings.enable_skew,
            algorithm=settings.algorithm,
            ratio_threshold=settings.ratio_threshold,
            **alignment_kwargs), f'{settings.algorithm} feature detection'
        return res

    if isinstance(settings, AlignmentSettingsPixels):
        return get_transform_pixel(
            get_data_file_data(user_id, file_id)[0],
            get_data_file_data(user_id, ref_file_id)[0],
            enable_rot=settings.enable_rot,
            enable_scale=settings.enable_scale,
            enable_skew=settings.enable_skew), 'pixel matching'

    raise ValueError('Unknown alignment mode "{}"'.format(settings.mode))
