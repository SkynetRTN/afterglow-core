"""
Afterglow Core: image alignment job plugin
"""

import re
from datetime import datetime
from typing import List as TList, Optional

from marshmallow.fields import Integer, List, Nested
from astropy.wcs import WCS
from flask import current_app

from skylib.astrometry import Solver, solve_field_glob

from ...database import db
from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean, Float
from ...errors import ValidationError
from ..data_files import create_data_file, get_data_file, get_data_file_data, get_root, save_data_file
from .source_extraction_job import (
    SourceExtractionSettings, run_source_extraction_job)


__all__ = ['WcsCalibrationJob']


WCS_REGEX = re.compile(
    r'^'
    # Paper I, Table 1
    r'(WCSAXES[A-Z]?)|'
    r'(CRVAL[1-9]\d?[A-Z]?)|'
    r'(CRPIX[1-9]\d?[A-Z]?)|'
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
    # DSS-specific keywords causing WCSLib to interpret it as DSS distortions
    r'(AMD(RE)?[XY]\d\d?)|'
    r'(CNPIX[1-9]\d?)|'
    r'(PPO[1-9])|'
    r'([XY]PIXELSZ)|'
    r'(PLT((RA[HMS])|(DEC(SN|[DMS]))))|'
    # The following must be kept intact if present and not set by solve_field()
    # r'(EQUINOX[A-Z]?)|'
    # r'(EPOCH)|'
    # r'(MJD-OBS)|'
    # r'(OBSGEO-[XYZ])|'  # Paper III, Table 13, but used not only for spectral
    r'$'
)


class WcsCalibrationSettings(AfterglowSchema):
    ra_hours: Optional[float] = Float(dump_default=None)
    dec_degs: Optional[float] = Float(dump_default=None)
    radius: float = Float(dump_default=180)
    min_scale: float = Float(dump_default=0.1)
    max_scale: float = Float(dump_default=60)
    parity: Optional[bool] = Boolean(truthy={True, 1, 'negative'}, falsy={False, 0, 'positive'}, dump_default=None)
    sip_order: int = Integer(dump_default=0)
    crpix_center: bool = Boolean(dump_default=True)
    max_sources: Optional[int] = Integer(dump_default=100)


class WcsCalibrationJobResult(JobResult):
    file_ids: TList[int] = List(Integer(), dump_default=[])


solver = None


class WcsCalibrationJob(Job):
    """
    Astrometric calibration job
    """
    type = 'wcs_calibration'
    description = 'Plate-solve Images'

    result: WcsCalibrationJobResult = Nested(WcsCalibrationJobResult, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: WcsCalibrationSettings = Nested(WcsCalibrationSettings, dump_default={})
    source_extraction_settings: SourceExtractionSettings = Nested(SourceExtractionSettings, dump_default=None)
    inplace: bool = Boolean(dump_default=True)

    def _callback(self):
        """
        Callback periodically called by Astrometry.net C code while solving

        :return: True if solution should continue, False if it should stop
        """
        try:
            return self.state.status != 'canceled'
        except KeyboardInterrupt:
            self.state.status = 'canceled'
            return False

    def run(self):
        global solver

        settings = self.settings

        if settings.ra_hours is not None and not 0 <= settings.ra_hours < 24:
            raise ValidationError('settings.ra_hours', 'RA not within range [0,24)', 422)
        if settings.dec_degs is not None and not -90 <= settings.dec_degs <= 90:
            raise ValidationError('settings.dec_degs', 'Dec not within range [-90,90]', 422)
        if settings.radius <= 0:
            raise ValidationError('settings.radius', 'Field search radius must be positive', 422)
        if settings.min_scale >= settings.max_scale:
            raise ValidationError('settings.min_scale', 'Minimum scale must be strictly less than maximum scale', 422)
        if settings.sip_order < 0:
            raise ValidationError('settings.sip_order', 'SIP order must be non-negative', 422)
        if settings.max_sources < 1:
            raise ValidationError('settings.max_sources', 'Maximum number of sources must be positive', 422)

        if not self.file_ids:
            return

        source_extraction_settings = self.source_extraction_settings or SourceExtractionSettings()
        # Don't discard saturated stars because we need max_sources brightest sources
        source_extraction_settings.discard_saturated = 0

        root = get_root(self.user_id)

        if solver is None:
            # Initialize the solver on first use; job worker processes are single-threaded, so we shouldn't care about
            # locking
            solver = Solver(current_app.config['ANET_INDEX_PATH'])

        for i, file_id in enumerate(self.file_ids):
            try:
                data, hdr = get_data_file_data(self.user_id, file_id)
                height, width = data.shape

                # Extract sources
                sources = run_source_extraction_job(
                    self, source_extraction_settings, [file_id], stage=2*i, total_stages=2*len(self.file_ids))[0]
                xy = [(source.x, source.y) for source in sources]
                fluxes = [source.flux for source in sources]

                ra_hours, dec_degs = settings.ra_hours, settings.dec_degs
                if ra_hours is None and dec_degs is None:
                    # Guess starting RA and Dec from WCS in the image header
                    # noinspection PyBroadException
                    try:
                        hdr['CRVAL1'] %= 360  # Ensure RA is in [0, 360) range
                        wcs = WCS(hdr, relax=True)
                        if wcs.has_celestial:
                            ra_hours, dec_degs = wcs.all_pix2world((width - 1)/2, (height - 1)/2, 0)
                            ra_hours %= 360
                            ra_hours /= 15
                    except Exception:
                        pass
                if ra_hours is None and dec_degs is None:
                    # Guess starting RA and Dec from MaxIm DL FITS keywords
                    for name in ('OBJRA', 'TELRA', 'RA'):
                        try:
                            h, m, s = hdr[name].split(':')
                            ra_hours = int(h) + int(m)/60 + float(s.replace(',', '.'))/3600
                        except (KeyError, ValueError):
                            pass
                        else:
                            break
                    for name in ('OBJDEC', 'TELDEC', 'DEC'):
                        try:
                            d, m, s = hdr[name].split(':')
                            dec_degs = (abs(int(d)) + int(m)/60 + float(s.replace(',', '.'))/3600) * \
                                (1 - d.strip().startswith('-'))
                        except (KeyError, ValueError):
                            pass
                        else:
                            break

                # Run Astrometry.net; allow to abort the job by calling back from the engine into Python code
                solution = solve_field_glob(
                    solver, xy, fluxes,
                    width=width,
                    height=height,
                    ra_hours=ra_hours or 0,
                    dec_degs=dec_degs or 0,
                    radius=settings.radius,
                    min_scale=settings.min_scale,
                    max_scale=settings.max_scale,
                    parity=settings.parity,
                    sip_order=settings.sip_order,
                    crpix_center=settings.crpix_center,
                    max_sources=settings.max_sources,
                    retry_lost=False,
                    callback=self._callback)
                if self.state.status == 'canceled':
                    raise KeyboardInterrupt('Solving field aborted')
                if solution.wcs is None:
                    raise RuntimeError('WCS solution not found')

                # Remove all existing WCS-related keywords so that they don't mess up the new WCS
                for name in list(hdr):
                    if WCS_REGEX.match(name):
                        del hdr[name]

                hdr.add_history(
                    f'[{datetime.utcnow()}] WCS calibration obtained by Afterglow with index {solution.index_name} '
                    f'from {solution.n_field} sources; matched sources: {solution.n_match}, '
                    f'conflicts: {solution.n_conflict}, log-odds: {solution.log_odds}')

                # Overwrite WCS in FITS header; preserve epoch of observation
                orig_kw = {
                    name: (hdr[name], hdr.comments[name]) if hdr.comments[name] else hdr[name]
                    for name in ('DATE-OBS', 'MJD-OBS', 'DATEREF', 'MJDREFI', 'MJDREFF') if name in hdr
                }
                hdr.update(solution.wcs.to_header(relax=True))
                for name, val in orig_kw.items():
                    hdr[name] = val

                try:
                    if self.inplace:
                        # Overwrite the original data file
                        save_data_file(root, file_id, data, hdr)
                    else:
                        hdr.add_history(
                            'Original data file: {}'.format(get_data_file(self.user_id, file_id).name or file_id))
                        file_id = create_data_file(
                            self.user_id, None, root, data, hdr, duplicates='append',
                            session_id=self.session_id).id
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    raise

                self.result.file_ids.append(file_id)
            except Exception as e:
                self.add_error(e, {'file_id': self.file_ids[i]})
            finally:
                self.update_progress(100, 2*i + 1, 2*len(self.file_ids))
