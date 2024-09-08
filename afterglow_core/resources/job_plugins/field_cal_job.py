"""
Afterglow Core: photometric calibration job plugin
"""

from datetime import datetime
from typing import List as TList, Optional, Tuple

from marshmallow.fields import Integer, List, Nested
import numpy
from numpy import (
    arange, argsort, array, asarray, clip, cos, deg2rad, degrees, inf,
    isfinite, log10, nan, ndarray, polyfit, sin, sqrt, transpose, where)
from scipy.spatial import cKDTree
from scipy.optimize import brenth
from astropy.wcs import WCS

from skylib.util.angle import angdist
from skylib.util.fits import get_fits_time
from skylib.util.stats import chauvenet, weighted_median, weighted_quantile

from ...models import (
    Job, JobResult, CatalogSource, FieldCal, FieldCalResult, Mag, PhotSettings,
    PhotometryData, SourceExtractionData, get_source_radec)
from ..data_files import get_data_file_fits
from ..field_cals import get_field_cal
from ..catalogs import catalogs as known_catalogs
from .catalog_query_job import run_catalog_query_job
from .source_extraction_job import (
    SourceExtractionSettings, run_source_extraction_job)
from .photometry_job import run_photometry_job


__all__ = ['FieldCalJob']


class FieldCalJobResult(JobResult):
    data: TList[FieldCalResult] = List(Nested(FieldCalResult), dump_default=[])


class FieldCalJob(Job):
    type = 'field_cal'
    description = 'Photometric Calibration'

    result: FieldCalJobResult = Nested(FieldCalJobResult, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    field_cal: FieldCal = Nested(FieldCal, dump_default={})
    source_extraction_settings: SourceExtractionSettings = Nested(
        SourceExtractionSettings, dump_default=None)
    photometry_settings: PhotSettings = Nested(PhotSettings, dump_default=None)

    def run(self):
        if not getattr(self, 'file_ids', None):
            return

        # If ID or name is supplied for the field cal, this is a reference
        # to a stored field cal; get it from the user's field cal table and
        # optionally override fields that were explicitly set by the user
        field_cal = self.field_cal
        id_or_name = getattr(field_cal, 'id', None)
        if id_or_name is None:
            id_or_name = getattr(field_cal, 'name', None)
        if id_or_name is not None:
            stored_field_cal = get_field_cal(self.user_id, id_or_name)
            for name, val in field_cal.to_dict().items():
                if name not in ('id', 'name'):
                    setattr(stored_field_cal, name, val)
            field_cal = stored_field_cal

        source_extraction_settings = getattr(
            self, 'source_extraction_settings', None)
        if source_extraction_settings is not None:
            # Detect sources using settings provided
            detected_sources = run_source_extraction_job(
                self, self.source_extraction_settings, self.file_ids,
                stage=0, total_stages=2)[0]
            if not detected_sources:
                raise RuntimeError('Could not detect any sources')
        else:
            detected_sources = []

        catalog_sources = getattr(field_cal, 'catalog_sources', None)
        if not catalog_sources and not getattr(field_cal, 'catalogs', None):
            raise ValueError(
                'Missing either catalog sources or catalog list in field '
                'cal{}'.format(
                    ' "{}"'.format(field_cal.name)
                    if getattr(field_cal, 'name', None) else ''))

        if catalog_sources:
            # Convert catalog magnitudes to Mag instances (not deserialized
            # automatically)
            for source in catalog_sources:
                for name, val in getattr(source, 'mags', {}).items():
                    if isinstance(val, dict):
                        source.mags[name] = Mag(**val)
            self.run_for_sources(catalog_sources, detected_sources)
        else:
            # No input catalog sources, query the specified catalogs, stop
            # if succeeded
            for i, catalog in enumerate(field_cal.catalogs):
                try:
                    catalog_sources = run_catalog_query_job(
                        self, [catalog], file_ids=self.file_ids,
                        skip_failed=True)
                    if not catalog_sources:
                        raise ValueError('No catalog sources found')
                    self.run_for_sources(catalog_sources, detected_sources)
                except Exception as e:
                    if i < len(field_cal.catalogs) - 1:
                        self.add_warning(
                            'Calibration failed for catalog "{}" [{}]'
                            .format(catalog, e))
                    else:
                        raise

    def run_for_sources(self, catalog_sources: TList[CatalogSource],
                        detected_sources: TList[SourceExtractionData]) -> None:
        """
        Perform calibration given a list of catalog sources (either supplied by
        the caller or retrieved from a single catalog) and an optional list of
        detected sources

        :param catalog_sources: list of catalog sources
        :param detected_sources: list of detected sources obtained from
            :func:`run_source_extraction_job`

        :return: None
        """
        file_ids = self.file_ids  # alias

        # Make sure that each input catalog source has a unique ID; it will
        # be used later to match photometry results to catalog sources
        prefix = '{}_{}_'.format(
            datetime.utcnow().strftime('%Y%m%d%H%M%S'), self.id)
        source_ids = set()
        for i, source in enumerate(catalog_sources):
            id = getattr(source, 'id', None)
            if id is None:
                # Auto-assign source ID
                source.id = id = prefix + str(i + 1)
            if getattr(source, 'file_id', None) is not None:
                id = (id, source.file_id)
            if id in source_ids:
                if isinstance(id, tuple):
                    raise ValueError(
                        'Non-unique source ID "{0[0]}" for file ID '
                        '{0[1]}'.format(id))
                else:
                    raise ValueError('Non-unique source ID "{}"'.format(id))
            source_ids.add(id)

        wcss, epochs = {}, {}
        variable_check_tol = getattr(self.field_cal, 'variable_check_tol', 5)
        if variable_check_tol and any(
                None in (getattr(source, 'ra_hours', None),
                         getattr(source, 'dec_degs'))
                for source in catalog_sources) or \
                getattr(self, 'source_extraction_settings', None) is not None:
            for file_id in file_ids:
                # noinspection PyBroadException
                try:
                    with get_data_file_fits(self.user_id, file_id) as f:
                        hdr = f[0].header
                except Exception:
                    pass
                else:
                    epoch = get_fits_time(hdr)[0]
                    if epoch is not None:
                        epochs[file_id] = epoch
                    # noinspection PyBroadException
                    try:
                        wcs = WCS(hdr, relax=True)
                        if wcs.has_celestial:
                            wcs.wcs.crval[0] %= 360
                        else:
                            wcs = None
                    except Exception:
                        wcs = None
                    if wcs is not None:
                        wcss[file_id] = wcs

        if variable_check_tol:
            # To exclude known variable stars from the list of catalog sources,
            # get all variable stars in all fields
            var_stars = {}
            for file_id in file_ids:
                # noinspection PyBroadException
                try:
                    var_stars[file_id] = run_catalog_query_job(
                        self, ['VSX'], file_ids=[file_id])
                except Exception:
                    # No WCS?
                    var_stars[file_id] = []
            unique_var_stars = list(
                {star.id: star for star in sum(var_stars.values(), [])}
                .values())
            for i, source in enumerate(list(catalog_sources)):
                file_id = getattr(source, 'file_id', None)
                if file_id is None:
                    epoch = wcs = None
                else:
                    epoch = epochs.get(source.file_id, None)
                    wcs = wcss.get(source.file_id, None)
                try:
                    ra, dec = get_source_radec(source, epoch, wcs)
                except Exception as e:
                    self.add_warning(
                        'Could not check variability for source {}: not '
                        'enough info to calculate source RA/Dec [{}]'
                        .format(getattr(source, 'id', None) or
                                '#'.format(i + 1), e))
                    continue
                file_id = getattr(source, 'file_id', None)
                for star in var_stars[file_id] if file_id is not None \
                        else unique_var_stars:
                    if degrees(angdist(
                            ra, dec, star.ra_hours, star.dec_degs))*3600 < \
                            variable_check_tol:
                        catalog_sources.remove(source)
                        break

        if detected_sources:
            #  Match detected sources to input catalog sources by XY position
            #  in each image
            tol = getattr(self.field_cal, 'source_match_tol', None)
            if tol is None:
                raise ValueError('Missing catalog source match tolerance')
            if tol <= 0:
                raise ValueError(
                    'Positive catalog source match tolerance expected')
            matching_catalog_sources = []
            catalog_sources_for_file = {file_id: [] for file_id in file_ids}
            for catalog_source in catalog_sources:
                catalog_source_file_id = getattr(
                    catalog_source, 'file_id', None)
                if getattr(catalog_source, 'x', None) is None or \
                        getattr(catalog_source, 'y', None) is None:
                    # Require RA/Dec for a source and WCS for each data file
                    if getattr(catalog_source, 'ra_hours', None) is None or \
                            getattr(catalog_source, 'dec_degs', None) is None \
                            or catalog_source_file_id is not None and \
                            wcss.get(catalog_source_file_id, None) is None or \
                            catalog_source_file_id is None and all(
                                wcss.get(file_id, None) is None
                                for file_id in file_ids):
                        continue
                if catalog_source_file_id is None:
                    for file_id in file_ids:
                        catalog_sources_for_file[file_id].append(
                            catalog_source)
                else:
                    catalog_sources_for_file[catalog_source.file_id].append(
                        catalog_source)
            catalog_source_kdtree_for_file = {}
            catalog_source_xy_for_file = {}
            for file_id, catalog_source_list in catalog_sources_for_file \
                    .items():
                if not catalog_source_list:
                    catalog_source_kdtree_for_file[file_id] = None
                    continue
                epoch, wcs = epochs.get(file_id, None), wcss.get(file_id, None)
                data = []
                for source in catalog_source_list:
                    x = getattr(source, 'x', None)
                    if x is None:
                        x = nan
                    y = getattr(source, 'y', None)
                    if y is None:
                        y = nan
                    if wcs is None:
                        ra = dec = pm_epoch = nan
                        pm_sky = pm_pos_angle_sky = 0
                        pm_pixel = pm_pos_angle_pixel = 0
                    else:
                        ra = getattr(source, 'ra_hours', None)
                        if ra is None:
                            ra = nan
                        else:
                            ra *= 15  # WCS calculations are in degrees
                        dec = getattr(source, 'dec_degs', None)
                        if dec is None:
                            dec = nan
                        if epoch is None:
                            pm_epoch = nan
                            pm_sky = pm_pos_angle_sky = 0
                            pm_pixel = pm_pos_angle_pixel = 0
                        else:
                            pm_epoch = getattr(source, 'pm_epoch', None)
                            if pm_epoch is None:
                                pm_epoch = nan
                                pm_sky = pm_pos_angle_sky = 0
                                pm_pixel = pm_pos_angle_pixel = 0
                            else:
                                pm_sky = getattr(source, 'pm_sky', 0)
                                pm_pos_angle_sky = getattr(
                                    source, 'pm_pos_angle_sky', 0)
                                pm_pixel = getattr(source, 'pm_pixel', 0)
                                pm_pos_angle_pixel = getattr(
                                    source, 'pm_pos_angle_pixel', 0)
                    data.append(
                        [x, y, ra, dec, pm_epoch, pm_sky, pm_pos_angle_sky,
                         pm_pixel, pm_pos_angle_pixel])
                x, y, ra, dec, pm_epoch, pm_sky, pm_pos_angle_sky, pm_pixel, \
                    pm_pos_angle_pixel = transpose(data)
                if wcs is not None:
                    # Prefer RA/Dec to XY if available and have a WCS
                    have_radec = isfinite(ra) & isfinite(dec)
                    if have_radec.any():
                        # Apply RA/Dec proper motions if present and have epoch
                        if epoch is not None:
                            have_pm = have_radec & isfinite(pm_epoch)
                            if have_pm.any():
                                mu = pm_sky*array(
                                    [dt.total_seconds()
                                     for dt in (epoch - pm_epoch[have_pm])])
                                theta = deg2rad(pm_pos_angle_sky[have_pm])
                                cd = clip(
                                    cos(deg2rad(dec[have_pm])), 1e-7, None)
                                ra[have_pm] += mu*sin(theta)/cd
                                ra[have_pm] %= 360
                                dec[have_pm] = clip(
                                    dec[have_pm] + mu*cos(theta), -90, 90)
                        x[have_radec], y[have_radec] = wcs.all_world2pix(
                            ra[have_radec], dec[have_radec], 1, quiet=True)
                if epoch is not None:
                    # Also apply proper motion in pixels, assuming that it does
                    # not conflict with RA/Dec PM
                    have_pm = isfinite(pm_epoch) & (pm_pixel != 0)
                    if have_pm.any():
                        mu = pm_pixel[have_pm]*asarray(
                            [dt.total_seconds()
                             for dt in (epoch - pm_epoch[have_pm])])
                        theta = deg2rad(pm_pos_angle_pixel[have_pm])
                        x[have_pm] += mu*cos(theta)
                        y[have_pm] += mu*sin(theta)
                # Build k-d tree from catalog source XYs
                xy = transpose([x, y])
                catalog_source_xy_for_file[file_id] = xy
                catalog_source_kdtree_for_file[file_id] = cKDTree(xy)

            # Build k-d tree from detected source XYs for each file ID
            detected_sources_for_file = {}
            for source in detected_sources:
                detected_sources_for_file.setdefault(source.file_id, []) \
                    .append(source)
            detected_source_kdtree_for_file = {
                file_id: cKDTree([(source.x, source.y) for source in sources])
                for file_id, sources in detected_sources_for_file.items()
            }

            for source in detected_sources:
                file_id = source.file_id
                catalog_source, match_found = None, False
                tree = catalog_source_kdtree_for_file[file_id]
                if tree is not None:
                    catalog_source_list = catalog_sources_for_file[file_id]
                    i = tree.query(
                        [source.x, source.y], distance_upper_bound=tol)[1]
                    if i < len(catalog_source_list):
                        catalog_source = catalog_source_list[i]
                        xc, yc = catalog_source_xy_for_file[file_id][i]

                        # Make sure that all matches are unique by making
                        # a reverse query: the given image source must be
                        # the nearest neighbor for its matching catalog source
                        detected_source_list = \
                            detected_sources_for_file[file_id]
                        tree = detected_source_kdtree_for_file[file_id]
                        j = tree.query([xc, yc], distance_upper_bound=tol)[1]
                        if j < len(detected_source_list) and \
                                detected_source_list[j] is source:
                            match_found = True
                if match_found:
                    # Copy catalog source data to extracted source and set
                    # the latter as a new catalog source
                    for attr in ('id', 'catalog_name', 'mags', 'label',
                                 'mag', 'mag_error'):
                        val = getattr(catalog_source, attr, None)
                        if val is not None:
                            setattr(source, attr, val)
                    matching_catalog_sources.append(source)
            if not matching_catalog_sources:
                raise RuntimeError(
                    'Could not match any detected sources to the catalog '
                    'sources provided')
            catalog_sources = matching_catalog_sources

        photometry_settings = getattr(self, 'photometry_settings', None)
        if photometry_settings is not None:
            # Do batch photometry using refstar positions; explicitly disable
            # photometric calibration even if present in data file headers
            # by setting field_cal_results to False since we need raw
            # (uncalibrated) mags here
            total_stages = 1 + int(
                getattr(self, 'source_extraction_settings', None) is not None)
            phot_data = [source for source in run_photometry_job(
                self, photometry_settings, file_ids, catalog_sources,
                stage=total_stages - 1, total_stages=total_stages)
                if source.mag]
            if not phot_data:
                raise RuntimeError('No catalog sources could be photometered')
        else:
            # If photometry is disabled, use instrumental magnitudes provided
            # by the user
            phot_data = catalog_sources
            if len(file_ids) > 1:
                if any(getattr(source, 'file_id', None) is None
                       for source in phot_data):
                    raise ValueError(
                        '"file_id" is required for all sources when '
                        'photometry is not enabled')
            else:
                # Assume the same file ID for all sources if processing
                # a single file
                file_id = file_ids[0]
                for source in phot_data:
                    if getattr(source, 'file_id', None) is None:
                        source.file_id = file_id
            if any(getattr(source, 'mag', None) is None
                   for source in phot_data):
                raise ValueError(
                    '"mag" is required for all sources when photometry is not '
                    'enabled')

            # Get filters from data file headers (will need them to map
            # to catalog mags
            filters = {}
            for source in phot_data:
                file_id = source.file_id
                try:
                    source.filter = filters[file_id]
                except KeyError:
                    # noinspection PyBroadException
                    try:
                        with get_data_file_fits(self.user_id, file_id) as f:
                            source.filter = f[0].header.get('FILTER')
                    except Exception:
                        source.filter = None
                    filters[file_id] = source.filter

        min_snr = getattr(self.field_cal, 'min_snr', None)
        max_snr = getattr(self.field_cal, 'max_snr', None)
        if min_snr or max_snr:
            # Exclude sources based on SNR
            if not min_snr:
                min_snr = 0
            if not max_snr:
                max_snr = inf
            new_phot_data = []
            for source in phot_data:
                mag_error = getattr(source, 'mag_error', 0)
                if mag_error and not min_snr <= 1/mag_error <= max_snr:
                    continue
                new_phot_data.append(source)
            phot_data = new_phot_data
            if not phot_data:
                raise RuntimeError('All sources violate SNR constraints')

        # Initialize custom filter mapping
        filter_lookup = {
            catalog_name: known_catalogs[catalog_name].filter_lookup
            for catalog_name in {
                catalog_source.catalog_name
                for catalog_source in catalog_sources
                if getattr(catalog_source, 'catalog_name', '')}
            if catalog_name in known_catalogs and
            getattr(known_catalogs[catalog_name], 'filter_lookup', None)
        }
        for catalog_name, lookup in getattr(
                self.field_cal, 'custom_filter_lookup', {}).items():
            filter_lookup.setdefault(catalog_name, {}).update(lookup)

        # For each data file ID, match photometry results to catalog sources
        # and use (mag, ref_mag) pairs to obtain zero point
        context = dict(numpy.__dict__)
        eps = 1e-7
        all_sources = []
        cal_results = {}
        for file_id in file_ids:
            sources = []
            for source in [source for source in phot_data
                           if source.file_id == file_id]:
                try:
                    catalog_source = [catalog_source
                                      for catalog_source in catalog_sources
                                      if catalog_source.id == source.id][0]
                except IndexError:
                    continue

                # Get reference magnitude for the current filter
                flt = getattr(source, 'filter', None)
                try:
                    mag = catalog_source.mags[flt]
                except (AttributeError, KeyError):
                    # No magnitude available for the current filter+catalog;
                    # try custom filter lookup
                    # noinspection PyBroadException
                    try:
                        try:
                            expr = filter_lookup[
                                catalog_source.catalog_name][flt]
                        except KeyError:
                            # For unknown filters, try the default
                            # mapping if any
                            expr = filter_lookup[
                                catalog_source.catalog_name]['*']
                        # Evaluate magnitude expression in the NumPy-enabled
                        # context extended with mags available for the current
                        # catalog source
                        ctx = dict(context)
                        ctx.update(
                            {f: m.value
                             for f, m in catalog_source.mags.items()})
                        mag = Mag(value=eval(expr, ctx, {}))

                        # Calculate the resulting magnitude error by coadding
                        # contributions from each filter
                        err = 0
                        for f, m in catalog_source.mags.items():
                            e = getattr(m, 'error', None)
                            if e:
                                # Partial derivative of final mag with resp. to
                                # the current filter
                                ctx[f] += eps
                                # noinspection PyBroadException
                                try:
                                    err += ((eval(expr, ctx, {}) -
                                             mag.value)/eps*e)**2
                                except Exception:
                                    pass
                                finally:
                                    ctx[f] = m.value
                        if err:
                            mag.error = sqrt(err)
                    except Exception:
                        # No magnitude available for the current
                        # filter+catalog; skip this source
                        continue

                m = getattr(mag, 'value', None)
                if m is None:
                    # Missing catalog magnitude value
                    continue
                source.ref_mag = m
                e = getattr(mag, 'error', None)
                if e:
                    source.ref_mag_error = e
                source.catalog_name = catalog_source.catalog_name
                sources.append(source)

            if not sources:
                self.add_error(
                    ValueError('No calibration sources'), {'file_id': file_id})
                continue
            m0, m0_error, limmag = calc_solution(sources)
            cal_results[file_id] = (m0, m0_error, limmag, sources)
            all_sources += sources

        source_inclusion_percent = getattr(
            self.field_cal, 'source_inclusion_percent', None)
        if source_inclusion_percent:
            # Keep only sources that are present in the given fraction
            # of images
            nmin = max(int(source_inclusion_percent/100 *
                           len(cal_results) + 0.5), 1)
            source_ids_to_keep, source_ids_to_remove = [], []
            for source in all_sources:
                id = source.id
                if id in source_ids_to_keep or id in source_ids_to_remove:
                    continue
                if len([s for s in all_sources
                        if s.id == id and s.file_id in cal_results]) < nmin:
                    source_ids_to_remove.append(id)
                else:
                    source_ids_to_keep.append(id)
            if source_ids_to_remove:
                if source_ids_to_keep:
                    all_sources = [source for source in all_sources
                                   if source.id in source_ids_to_keep]
                    for file_id in list(cal_results.keys()):
                        sources = [source
                                   for source in cal_results[file_id][-1]
                                   if source.id in source_ids_to_keep]
                        if sources:
                            m0, m0_error, limmag = calc_solution(sources)
                            cal_results[file_id] = (m0, m0_error, limmag,
                                                    sources)
                        else:
                            del cal_results[file_id]
                            self.add_error(ValueError(
                                'No calibration sources satisfy inclusion '
                                'percent constraint'), {'file_id': file_id})
                else:
                    raise ValueError(
                        'No sources found that are present in ' +
                        'all images' if source_inclusion_percent >= 100 else
                        'at least one image' if nmin == 1 else
                        'at least {:d} images'.format(nmin))

        max_star_rms = getattr(self.field_cal, 'max_star_rms', 0)
        max_stars = getattr(self.field_cal, 'max_stars', 0)
        if len(cal_results) > 1 and (max_star_rms > 0 or max_stars > 0):
            # Recalculate the calibration using only best stars in terms of
            # RMS for all images
            sources_used = {
                id: [source for source in all_sources if source.id == id]
                for id in set(source.id for source in all_sources)
            }
            sources_used = {id: sources for id, sources in sources_used.items()
                            if len(sources) > 1}
            if not sources_used:
                raise ValueError(
                    'No sources common to at least two data files, cannot '
                    'calculate corrected refstar magnitude RMS; disable max '
                    'star RMS and max star number constraints')
            source_ids = array(list(sources_used.keys()))
            source_rms = array(
                [array(
                    [source.mag + cal_results[source.file_id][0]
                     for source in sources_used[id]]).std()
                 for id in source_ids])
            order = argsort(source_rms)
            source_ids = source_ids[order]
            source_rms = source_rms[order]
            if max_star_rms > 0:
                source_ids = source_ids[source_rms < max_star_rms]
                if not len(source_ids):
                    raise ValueError(
                        'No sources satisfy max star RMS constraint')
            if max_stars > 0:
                source_ids = source_ids[:max_stars]
                for file_id in list(cal_results.keys()):
                    sources = [source for source in cal_results[file_id][-1]
                               if source.id in source_ids]
                    if sources:
                        m0, m0_error, limmag = calc_solution(sources)
                        cal_results[file_id] = (m0, m0_error, limmag, sources)
                    else:
                        del cal_results[file_id]
                        self.add_error(ValueError(
                            'No calibration sources satisfy RMS constraints'),
                            {'file_id': file_id})

        result_data = []
        for file_id, (m0, m0_error, limmag, sources) in cal_results.items():
            result_data.append(FieldCalResult(
                file_id=file_id,
                phot_results=sources,
                zero_point_corr=m0,
                zero_point_error=m0_error,
                limmag5=limmag,
            ))

            # Update photometric calibration info in data file header; use the
            # absolute zero point value instead of the correction relative to
            # PhotometrySettings.zero_point
            try:
                with get_data_file_fits(self.user_id, file_id, 'update') as f:
                    hdr = f[0].header
                    hdr['PHOT_M0'] = (
                        m0 + getattr(photometry_settings, 'zero_point', 0),
                        'Photometric zero point')
                    if m0_error:
                        hdr['PHOT_M0E'] = (
                            m0_error, 'Photometric zero point error')
                    if getattr(self.field_cal, 'name', None):
                        hdr['PHOT_CAL'] = self.field_cal.name, 'Field cal name'
                    elif getattr(self.field_cal, 'id', None):
                        hdr['PHOT_CAL'] = self.field_cal.id, 'Field cal ID'
            except Exception as e:
                self.add_warning(
                    'Data file ID {}: Error saving photometric calibration '
                    'info to FITS header [{}]'.format(file_id, e))

        object.__setattr__(self.result, 'data', result_data)


def sigma_eq(sigma2, sigmas2, b, m0):
    """
    Equation for finding sigma characterizing the goodness of fit

    :param sigma2: sigma squared
    :param sigmas2: array of individual point sigmas
    :param b: array of catalog minus image mags, same shape
    :param m0: current estimate of zero point

    :return: the value of sigma2 yielding zero result solves the equation
    """
    w = 1/(sigmas2 + sigma2)
    return (((b - m0)**2*w - 1)*w).sum()


def calc_solution(sources: TList[PhotometryData]) \
        -> Tuple[float, float, Optional[float]]:
    """
    Calculate photometric solution (zero point and error) given a list of
    sources with instrumental and catalog magnitudes

    :param sources: list of sources; each one must contain at least `mag`
        (instrumental magnitude) and `ref_mag` (catalog magnitude) attributes
        and optionally `mag_error` and `ref_mag_error` for the corresponding
        errors

    :return: zero point, its error, and 5-sigma limiting magnitude if available
    """
    # noinspection PyUnresolvedReferences
    mags, mag_errors, ref_mags, ref_mag_errors = transpose([
        (source.mag, getattr(source, 'mag_error', None) or 0,
         source.ref_mag, getattr(source, 'ref_mag_error', None) or 0)
        for source in sources
    ])
    snr = where(mag_errors > 0, 1/(10**(mag_errors/2.5) - 1), 0)

    b = ref_mags - mags
    good_stars = arange(len(b))
    sigmas2 = mag_errors**2 + ref_mag_errors**2
    no_errors = not sigmas2.any()
    if no_errors:
        sigmas2 = 0
    m0 = sigma2 = 0
    limmag = None
    weights = None
    for _ in range(1000):
        while True:
            if weights is None:
                rejected = chauvenet(
                    b, mean_type=1, sigma_type=1, max_iter=1)[0]
            else:
                bmed = weighted_median(b, weights)
                sigma68 = weighted_quantile(abs(b - bmed), weights, 0.683)
                rejected = chauvenet(
                    b, mean_override=bmed, sigma_override=sigma68,
                    max_iter=1)[0]
            if rejected.any():
                good = ~rejected
                mags = mags[good]
                snr = snr[good]
                b = b[good]
                if weights is not None:
                    weights = weights[good]
                good_stars = good_stars[good]
                if not no_errors:
                    sigmas2 = sigmas2[good]
            else:
                break

        if sigma2:
            m0 = (b/(sigmas2 + sigma2)).sum()/(1/(sigmas2 + sigma2)).sum()
        else:
            m0 = b.mean()

        # Limiting magnitude
        good = snr > 0
        if good.any():
            limmag_a, limmag_b = polyfit(mags[good] + m0, log10(snr[good]), 1)
            if limmag_a:
                limmag = (log10(5) - limmag_b)/limmag_a

        prev_sigma2 = sigma2
        sigma2 = ((b - m0)**2).sum()/len(b)
        if not no_errors:
            left, right = 0.9*sigma2, 1.1*sigma2
            for _ in range(1000):
                if sigma_eq(left, sigmas2, b, m0) * \
                        sigma_eq(right, sigmas2, b, m0) < 0:
                    break
                left *= 0.9
                right *= 1.1
            # noinspection PyBroadException
            try:
                sigma2 = brenth(sigma_eq, left, right, (sigmas2, b, m0))
            except Exception:
                # Unable to find the root; use unweighted sigma
                break
        if prev_sigma2 and abs(sigma2 - prev_sigma2) < 1e-8:
            break

        if not no_errors:
            weights: Optional[ndarray] = 1/(sigmas2 + sigma2)

    return m0, 1/sqrt((1/(sigmas2 + sigma2)).sum()), limmag
