"""
Afterglow Core: automatic batch cosmetic correction job plugin
"""

from __future__ import annotations

from typing import List as TList, Optional

import numpy as np
from marshmallow.fields import Integer, List, Nested

from skylib.combine.stacking import combine
from skylib.calibration.cosmetic import (
    correct_cols_and_pixels, flag_columns, flag_horiz, flag_pixels)
from skylib.util.fits import get_fits_exp_length, get_fits_time

from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean, Float
from ..data_files import (
    create_data_file, get_data_file_data, get_data_file_fits, get_data_file_db,
    get_root, save_data_file)


__all__ = ['CosmeticCorrectionJob', 'run_cosmetic_correction_job']


class CosmeticCorrectionSettings(AfterglowSchema):
    m_col: int = Integer(dump_default=10)
    nu_col: int = Integer(dump_default=0)
    m_pixel: int = Integer(dump_default=2)
    nu_pixel: int = Integer(dump_default=4)
    m_corr_col: int = Integer(dump_default=2)
    m_corr_pixel: int = Integer(dump_default=1)
    group_by_instrument: bool = Boolean(dump_default=True)
    group_by_filter: bool = Boolean(dump_default=True)
    group_by_exp_length: bool = Boolean(dump_default=False)
    max_group_len: int = Integer(dump_default=0)
    max_group_span_hours: float = Float(dump_default=0)
    min_group_sep_hours: float = Float(dump_default=0)


class CosmeticCorrectionJobResult(JobResult):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class CosmeticCorrectionJob(Job):
    """
    Cosmetic correction job
    """
    type = 'cosmetic'
    description = 'Intra-image Cosmetic Correction'

    result: CosmeticCorrectionJobResult = Nested(
        CosmeticCorrectionJobResult, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: CosmeticCorrectionSettings = Nested(
        CosmeticCorrectionSettings, dump_default={})
    inplace: bool = Boolean(dump_default=True)

    def run(self):
        self.result.file_ids = run_cosmetic_correction_job(
            self, self.settings, getattr(self, 'file_ids', []), self.inplace)


def group_key(user_id: int, file_id: int,
              settings: CosmeticCorrectionSettings) -> Optional[tuple]:
    """
    Generate key identifying a group of uniform images that will be stacked to
    obtain defect map that will be then applied to all images in the group

    :param user_id: job user ID
    :param file_id: data file ID
    :param settings: cosmetic correction settings

    :return: group key and exposure start time; None if data file does not
        exist
    """
    # noinspection PyBroadException
    try:
        with get_data_file_fits(user_id, file_id) as f:
            hdr = f[0].header
    except Exception:
        return

    # Always include image dimensions
    key = hdr.get('NAXIS1', None), hdr.get('NAXIS2', None)

    if settings.group_by_instrument:
        key += str(hdr.get('ORIGIN', '')) + '_' + \
            str(hdr.get('TELESCOP', '')) + '_' + str(hdr.get('INSTRUME', '')),
    if settings.group_by_filter:
        key += hdr.get('FILTER', ''),
    if settings.group_by_exp_length:
        key += get_fits_exp_length(hdr),

    return key, get_fits_time(hdr)[0]


def run_cosmetic_correction_job(
            job: Job,
            settings: Optional[CosmeticCorrectionSettings],
            job_file_ids: TList[int],
            inplace: bool = False,
            stage: int = 0, total_stages: int = 1) \
        -> TList[int]:
    """
    Cosmetic correction job body

    :param job: job class instance
    :param settings: cosmetic correction settings
    :param job_file_ids: data file IDs to process
    :param inplace: correct in place instead of creating a new data file
    :param stage: optional processing stage number; used to properly update
        the job progress if cropping is a part of other job
    :param total_stages: total number of stages in the enclosing job if any

    :return: list of generated/modified data file IDs
    """
    # Split files into groups by dimensions, instrument name, filter, and epoch
    groups = {}
    for file_id in job_file_ids:
        key, t = group_key(job.user_id, file_id, settings)
        if key is not None:
            groups.setdefault(key, []).append((t, file_id))
    # Sort images in each group by epoch; if no epoch, sort by file ID
    groups = [list(sorted(group)) for group in groups.values()]
    final_groups = []
    for group in groups:
        final_groups.append([group[0]])
        for t, file_id in group[1:]:
            if 0 < settings.max_group_len < len(final_groups[-1]) or \
                    settings.max_group_span_hours and t is not None and \
                    final_groups[-1][0][0] is not None and \
                    (t - final_groups[-1][0][0]).total_seconds > \
                    settings.max_group_span_hours*3600 or \
                    settings.min_group_sep_hours and t is not None and \
                    final_groups[-1][-1][0] is not None and \
                    (t - final_groups[-1][-1][0]).total_seconds > \
                    settings.min_group_sep_hours*3600:
                # Start a new group
                final_groups.append([(t, file_id)])
            else:
                # Continue the current group
                final_groups[-1].append((t, file_id))
    groups = [[file_id for _, file_id in group] for group in final_groups]
    if not groups:
        return []

    new_file_ids = []
    files_processed = 0
    for group in groups:
        if len(group) > 1:
            # Combine images in group
            fits = [get_data_file_fits(job.user_id, file_id)
                    for file_id in group]
            try:
                data = combine(fits, return_headers=False)[0]
            finally:
                for f in fits:
                    del f[0].data
                    f.close()
        else:
            # Rely on the image itself to extract cosmetic correction data
            data = get_data_file_data(job.user_id, group[0])[0]

        # Extract cosmetic correction data
        try:
            if data.dtype.name == 'float32':
                # Numba is slower for 32-bit floating point
                data = data.astype(np.float64)
            elif not data.dtype.isnative:
                # Non-native byte order is not supported by Numba
                data = data.byteswap().newbyteorder()
            initial_mask = flag_horiz(
                data, m=settings.m_col, nu=settings.nu_col)
            col_mask = flag_columns(initial_mask)
            pixel_mask = flag_pixels(
                data, col_mask, m=settings.m_pixel, nu=settings.nu_pixel)
        except Exception as e:
            job.add_error(
                e, {'file_id': ','.join(str(file_id) for file_id in group)})
            continue

        # Apply cosmetics data to all images in group
        for file_id in group:
            try:
                data, hdr = get_data_file_data(job.user_id, file_id)
                if data.dtype.name == 'float32':
                    data = data.astype(np.float64)
                elif not data.dtype.isnative:
                    data = data.byteswap().newbyteorder()
                data = correct_cols_and_pixels(
                    data, col_mask, pixel_mask, m_col=settings.m_corr_col,
                    m_pixel=settings.m_corr_pixel)

                if inplace:
                    with get_data_file_db(job.user_id) as adb:
                        try:
                            # Overwrite the original data file
                            save_data_file(
                                adb, get_root(job.user_id), file_id, data, hdr)
                            adb.commit()
                        except Exception:
                            adb.rollback()
                            raise
                else:
                    hdr.add_history(
                        'Original data file ID: {:d}'.format(file_id))
                    with get_data_file_db(job.user_id) as adb:
                        try:
                            file_id = create_data_file(
                                adb, None, get_root(job.user_id), data, hdr,
                                duplicates='append',
                                session_id=job.session_id).id
                            adb.commit()
                        except Exception:
                            adb.rollback()
                            raise

                new_file_ids.append(file_id)
                files_processed += 1
            except Exception as e:
                job.add_error(e, {'file_id': file_id})
            finally:
                job.update_progress(
                    (files_processed + 1)/len(job_file_ids)*100, stage,
                    total_stages)

    return new_file_ids
