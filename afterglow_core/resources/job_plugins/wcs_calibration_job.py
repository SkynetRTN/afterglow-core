"""
Afterglow Core: image alignment job plugin
"""

import re
from datetime import datetime
from typing import List as TList, Optional

from marshmallow.fields import Integer, List, Nested

from skylib.astrometry import Solver, solve_field

from ... import app
from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean, Float
from ...errors import ValidationError
from ..data_files import (
    create_data_file, get_data_file_data, get_data_file_db, get_root,
    save_data_file)
from .source_extraction_job import (
    SourceExtractionSettings, run_source_extraction_job)


__all__ = ['WcsCalibrationJob']


WCS_REGEX = re.compile(
    r'^'
    # Paper I, Table 1
    r'(WCSAXES[A-Z]?)|'
    r'(CRVAL[1-9]\d?[A-Z]?)|'
    r'(CRPIX[1-9]\d?[A-Z])|'
    r'(PC[1-9]\d?_[1-9]\d?[A-Z]?)|'
    r'(CDELT[1-9]\d?[A-Z]?)|'
    r'(CD[1-9]\d?_[1-9]\d?[A-Z]?)|'
    r'(CTYPE[1-9]\d?[A-Z]?)|'
    r'(CUNIT[1-9]\d?[A-Z]?)|'
    r'(PV[1-9]\d?_\d\d?[A-Z]?)|'
    r'(PS[1-9]\d?_\d\d?[A-Z]?)|'
    # Paper I, Table 2
    r'(WCSNAME[A-Z]?)|'
    r'(CRDER[1-9]\d?[A-Z]?)|'
    r'(CSYER[1-9]\d?[A-Z]?)|'
    r'(CROTA[1-9]\d?)|'
    # Paper II, Table 12
    r'(LONPOLE[A-Z]?)|'
    r'(LATPOLE[A-Z]?)|'
    r'(RADESYS[A-Z]?)|'
    # Paper IV (draft), Table 2
    r'(C[PQ]DIS[1-9]\d?[A-Z]?)|'
    r'(D[PQ][1-9]\d?[A-Z]?)|'
    r'(C[PQ]ERR[1-9]\d?[A-Z]?)|'
    r'(DVERR[1-9]\d?[A-Z]?)|'
    # SIP distortions
    r'([AB]P?_(ORDER|\d\d?_\d\d?)[A-Z]?)|'
    # TNX and ZPX distortions
    r'(WAT\d_\d\d\d)|'
    # The following must be kept intact if present and not set by solve_field()
    # r'(EQUINOX[A-Z]?)|'
    # r'(EPOCH)|'
    # r'(MJD-OBS)|'
    # r'(OBSGEO-[XYZ])|'  # Paper III, Table 13, but used not only for spectral
    r'$'
)


class WcsCalibrationSettings(AfterglowSchema):
    ra_hours = Float(default=0)  # type: float
    dec_degs = Float(default=0)  # type: float
    radius = Float(default=180)  # type: float
    min_scale = Float(default=0.1)  # type: float
    max_scale = Float(default=60)  # type: float
    parity = Boolean(
        truthy={True, 1, 'negative'},
        falsy={False, 0, 'positive'}, default=None)  # type: Optional[bool]
    sip_order = Integer(default=3)  # type: int
    crpix_center = Boolean(default=True)  # type: bool
    max_sources = Integer(default=100)  # type: Optional[int]


class WcsCalibrationJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: TList[int]


class WcsCalibrationJob(Job):
    """
    Astrometric calibration job
    """
    type = 'wcs_calibration'
    description = 'Plate-solve Images'

    result = Nested(
        WcsCalibrationJobResult, default={})  # type: WcsCalibrationJobResult
    file_ids = List(Integer(), default=[])  # type: TList[int]
    settings = Nested(
        WcsCalibrationSettings, default={})  # type: WcsCalibrationSettings
    source_extraction_settings = Nested(
        SourceExtractionSettings,
        default=None)  # type: SourceExtractionSettings
    inplace = Boolean(default=False)  # type: bool

    def run(self):
        settings = self.settings

        if settings.ra_hours is not None and not 0 <= settings.ra_hours < 24:
            raise ValidationError(
                'settings.ra_hours', 'RA not within range [0,24)', 422)
        if settings.dec_degs is not None and not -90 <= settings.dec_degs <= 90:
            raise ValidationError(
                'settings.dec_degs', 'Dec not within range [-90,90]', 422)
        if settings.radius <= 0:
            raise ValidationError(
                'settings.radius', 'Field search radius must be positive', 422)
        if settings.min_scale >= settings.max_scale:
            raise ValidationError(
                'settings.min_scale',
                'Minimum scale must be strictly less than maximum scale', 422)
        if settings.sip_order < 0:
            raise ValidationError(
                'settings.sip_order', 'SIP order must be non-negative', 422)
        if settings.max_sources < 1:
            raise ValidationError(
                'settings.max_sources',
                'Maximum number of sources must be positive', 422)

        if not self.file_ids:
            return

        source_extraction_settings = self.source_extraction_settings or \
            SourceExtractionSettings()
        if settings.max_sources is not None:
            source_extraction_settings.limit = settings.max_sources

        adb = get_data_file_db(self.user_id)
        root = get_root(self.user_id)

        solver = Solver(app.config['ANET_INDEX_PATH'])

        for i, file_id in enumerate(self.file_ids):
            try:
                data, hdr = get_data_file_data(self.user_id, file_id)

                # Extract sources
                sources = run_source_extraction_job(
                    self, source_extraction_settings, [file_id])
                xy = [(source.x, source.y) for source in sources]
                fluxes = [source.flux for source in sources]

                # Run Astrometry.net; allow to abort the job by calling back
                # from the engine into Python code
                solution = solve_field(
                    solver, xy, fluxes,
                    width=data.shape[1],
                    height=data.shape[0],
                    ra_hours=settings.ra_hours or 0,
                    dec_degs=settings.dec_degs or 0,
                    radius=settings.radius,
                    min_scale=settings.min_scale, max_scale=settings.max_scale,
                    parity=settings.parity,
                    sip_order=settings.sip_order,
                    crpix_center=settings.crpix_center,
                    max_sources=settings.max_sources,
                    retry_lost=False,
                    callback=lambda: 1)
                if solution.wcs is None:
                    raise RuntimeError('WCS solution not found')

                # Remove all existing WCS-related keywords so that they don't
                # mess up the new WCS if it doesn't have them
                for name in list(hdr):
                    if WCS_REGEX.match(name):
                        del hdr[name]

                hdr.add_history(
                    'WCS calibration obtained at {} with index {} from {} '
                    'sources; matched sources: {}, conflicts: {}, log-odds: '
                    '{}'.format(
                        datetime.utcnow(), solution.index_name,
                        solution.n_field, solution.n_match, solution.n_conflict,
                        solution.log_odds))

                # Overwrite WCS in FITS header; preserve epoch of observation
                orig_kw = {
                    name: (hdr[name], hdr.comments[name])
                    if hdr.comments[name] else hdr[name]
                    for name in (
                        'DATE-OBS', 'MJD-OBS', 'DATEREF', 'MJDREFI', 'MJDREFF')
                    if name in hdr
                }
                hdr.update(solution.wcs.to_header(relax=True))
                for name, val in orig_kw.items():
                    hdr[name] = val

                try:
                    if self.inplace:
                        # Overwrite the original data file
                        save_data_file(adb, root, file_id, data, hdr)
                    else:
                        hdr.add_history(
                            'Original data file ID: {:d}'.format(file_id))
                        file_id = create_data_file(
                            adb, None, root, data, hdr, duplicates='append',
                            session_id=self.session_id).id
                    adb.commit()
                except Exception:
                    adb.rollback()
                    raise

                self.result.file_ids.append(file_id)
            except Exception as e:
                self.add_error(
                    'Data file ID {}: {}'.format(self.file_ids[i], e))
            finally:
                self.state.progress = (i + 1)/len(self.file_ids)*100
                self.update()