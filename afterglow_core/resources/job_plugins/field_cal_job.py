"""
Afterglow Core: photometric calibration job plugin
"""

from datetime import datetime
from typing import List as TList, Tuple

from marshmallow.fields import Integer, List, Nested
import numpy
from astropy.wcs import WCS

from ...models import (
    Job, JobResult, CatalogSource, FieldCal, FieldCalResult, Mag, PhotSettings,
    PhotometryData, SourceExtractionData, get_source_radec, get_source_xy)
from ..data_files import get_data_file_fits, get_image_time
from ..field_cals import get_field_cal
from ..catalogs import catalogs as known_catalogs
from .catalog_query_job import run_catalog_query_job
from .source_extraction_job import (
    SourceExtractionSettings, run_source_extraction_job)
from .photometry_job import run_photometry_job


__all__ = ['FieldCalJob']


class FieldCalJobResult(JobResult):
    data: TList[FieldCalResult] = List(Nested(FieldCalResult), default=[])


class FieldCalJob(Job):
    type = 'field_cal'
    description = 'Photometric Calibration'

    result: FieldCalJobResult = Nested(FieldCalJobResult, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    field_cal: FieldCal = Nested(FieldCal, default={})
    source_extraction_settings: SourceExtractionSettings = Nested(
        SourceExtractionSettings, default=None)
    photometry_settings: PhotSettings = Nested(PhotSettings, default=None)

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
                update_progress=False)
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
                        self, [catalog], file_ids=self.file_ids)
                    self.run_for_sources(catalog_sources, detected_sources)
                except Exception as e:
                    if i < len(field_cal.catalogs):
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
            for file_id in self.file_ids:
                # noinspection PyBroadException
                try:
                    with get_data_file_fits(self.user_id, file_id) as f:
                        hdr = f[0].header
                except Exception:
                    pass
                else:
                    # noinspection PyBroadException
                    try:
                        epoch = get_image_time(hdr)
                    except Exception:
                        epoch = None
                    if epoch is not None:
                        epochs[file_id] = epoch
                    # noinspection PyBroadException
                    try:
                        wcs = WCS(hdr)
                        if not wcs.has_celestial:
                            wcs = None
                    except Exception:
                        wcs = None
                    if wcs is not None:
                        wcss[file_id] = wcs

        if variable_check_tol:
            # To exclude known variable stars from the list of catalog sources,
            # get all variable stars in all fields
            var_stars = {
                file_id: run_catalog_query_job(
                    self, ['VSX'], file_ids=[file_id])
                for file_id in self.file_ids}
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
                    ra, dec = numpy.radians(
                        get_source_radec(source, epoch, wcs))
                    ra *= 15
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
                    star_ra, star_dec = numpy.radians(
                        [star.ra_hours*15, star.dec_degs])
                    if numpy.degrees(
                            2*numpy.arcsin(numpy.sqrt(
                                numpy.sin((star_dec - dec)/2)**2 +
                                numpy.cos(star_dec)*numpy.cos(dec) *
                                numpy.sin((star_ra - ra)/2)**2)))*3600 < \
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
            for source in detected_sources:
                file_id = source.file_id
                catalog_source, match_found = None, False
                for catalog_source in catalog_sources:
                    if getattr(catalog_source, 'file_id', None) is None or \
                            catalog_source.file_id == file_id:
                        x, y = get_source_xy(
                            catalog_source, epochs.get(file_id, None),
                            wcss.get(file_id, None))
                        if numpy.hypot(x - source.x, y - source.y) < tol:
                            if any(source1.id == catalog_source.id and
                                   (getattr(source1, 'file_id', None) is
                                    None or source1.file_id == file_id)
                                   for source1 in matching_catalog_sources):
                                self.add_warning(
                                    'Data file ID {}: Multiple matches for '
                                    'catalog source "{}" within {} '
                                    'pixel{}'.format(
                                        file_id, catalog_source.id, tol,
                                        '' if tol == 1 else 's'))
                                break
                            match_found = True
                            break
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
            phot_data = [source for source in run_photometry_job(
                self, photometry_settings, self.file_ids, catalog_sources)
                if source.mag]
            if not phot_data:
                raise RuntimeError('No catalog sources could be photometered')
        else:
            # If photometry is disabled, use instrumental magnitudes provided
            # by the user
            phot_data = catalog_sources
            if len(self.file_ids) > 1:
                if any(getattr(source, 'file_id', None) is None
                       for source in phot_data):
                    raise ValueError(
                        '"file_id" is required for all sources when '
                        'photometry is not enabled')
            else:
                # Assume the same file ID for all sources if processing
                # a single file
                file_id = self.file_ids[0]
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
                max_snr = numpy.inf
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
        for file_id in self.file_ids:
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
                            mag.error = numpy.sqrt(err)
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
            m0, m0_error = calc_solution(sources)
            cal_results[file_id] = (m0, m0_error, sources)
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
                if len([s for s in all_sources if s.id == id]) < nmin:
                    source_ids_to_remove.append(id)
                else:
                    source_ids_to_keep.append(id)
            if source_ids_to_remove:
                if source_ids_to_keep:
                    all_sources = [source for source in all_sources
                                   if source.id in source_ids_to_keep]
                    for file_id in list(cal_results.keys()):
                        m0, m0_error, sources = cal_results[file_id]
                        sources = [source for source in sources
                                   if source.id in source_ids_to_keep]
                        if sources:
                            cal_results[file_id] = (m0, m0_error, sources)
                        else:
                            del cal_results[file_id]
                            self.add_error(ValueError(
                                'No calibration sources satisfy inclusion '
                                'percent constraint'), {'file_id': file_id})
                else:
                    raise ValueError(
                        'No sources found that are present in ' +
                        'all images' if nmin == len(self.file_ids) else
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
            source_ids = numpy.array(list(sources_used.keys()))
            source_rms = numpy.array(
                [numpy.array(
                    [source.mag + cal_results[source.file_id][0]
                     for source in sources_used[id]]).std()
                 for id in source_ids])
            order = numpy.argsort(source_rms)
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
                        m0, m0_error = calc_solution(sources)
                        cal_results[file_id] = (m0, m0_error, sources)
                    else:
                        del cal_results[file_id]
                        self.add_error(ValueError(
                            'No calibration sources satisfy RMS constraints'),
                            {'file_id': file_id})

        result_data = []
        for file_id, (m0, m0_error, sources) in cal_results.items():
            result_data.append(FieldCalResult(
                file_id=file_id,
                phot_results=sources,
                zero_point_corr=m0,
                zero_point_error=m0_error,
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

        self.result.data = result_data


def calc_solution(sources: TList[PhotometryData]) -> Tuple[float, float]:
    """
    Calculate photometric solution (zero point and error) given a list of
    sources with instrumental and catalog magnitudes

    :param sources: list of sources; each one must contain at least `mag`
        (instrumental magnitude) and `ref_mag` (catalog magnitude) attributes
        and optionally `mag_error` and `ref_mag_error` for the corresponding
        errors

    :return: zero point and its error
    """
    # noinspection PyUnresolvedReferences
    mags, mag_errors, ref_mags, ref_mag_errors = numpy.transpose([
        (source.mag, getattr(source, 'mag_error', None) or 0,
         source.ref_mag, getattr(source, 'ref_mag_error', None) or 0)
        for source in sources
    ])

    n = len(sources)
    while True:
        d = ref_mags - mags
        m0 = d.mean()
        m0_error = numpy.sqrt((mag_errors**2 + ref_mag_errors**2).sum())/n
        good = (numpy.abs(d - m0) < 3*d.std()).nonzero()[0]
        n_good = len(good)
        if n_good == n or n_good < 3:
            break
        n = n_good
        mags, mag_errors = mags[good], mag_errors[good]
        ref_mags, ref_mag_errors = ref_mags[good], ref_mag_errors[good]
    if abs(m0_error) < 1e-7:
        if n > 1:
            m0_error = d.std()/numpy.sqrt(n)
        else:
            m0_error = None

    return m0, m0_error
