"""
Afterglow Core: image cropping job plugin
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict as TDict, List as TList, Optional, Tuple

from marshmallow.fields import Integer, List, Nested
import numpy as np

from skylib.combine.cropping import get_auto_crop

from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean
from ...errors import ValidationError
from ..data_files import (
    create_data_file, get_data_file, get_data_file_data, get_data_file_db,
    get_root, save_data_file)


__all__ = ['CroppingJob', 'run_cropping_job']


def run_cropping_job(job: Job,
                     settings: Optional[CroppingSettings],
                     job_file_ids: TList[int],
                     inplace: bool = False,
                     masks: Optional[TDict[int, np.ndarray]] = None,
                     stage: int = 0, total_stages: int = 1) \
        -> TList[int]:
    """
    Image cropping job body; also used during alignment

    :param job: job class instance
    :param settings: cropping settings
    :param job_file_ids: data file IDs to process
    :param inplace: crop in place instead of creating a new data file
    :param masks: used by alignment job; contains the original data file masks
        to apply after cropping
    :param stage: optional processing stage number; used to properly update
        the job progress if cropping is a part of other job
    :param total_stages: total number of stages in the enclosing job if any

    :return: list of generated/modified data file IDs
    """
    if masks is None:
        masks = {}

    if settings:
        left = getattr(settings, 'left', None)
        if left is None:
            left = 0
        right = getattr(settings, 'right', None)
        if right is None:
            right = 0
        top = getattr(settings, 'top', None)
        if top is None:
            top = 0
        bottom = getattr(settings, 'bottom', None)
        if bottom is None:
            bottom = 0
    else:
        left = right = top = bottom = 0
    if left < 0:
        raise ValidationError(
            'settings.left', 'Left margin must be non-negative')
    if right < 0:
        raise ValidationError(
            'settings.right', 'Right margin must be non-negative')
    if top < 0:
        raise ValidationError(
            'settings.top', 'Top margin must be non-negative')
    if bottom < 0:
        raise ValidationError(
            'settings.bottom', 'Bottom margin must be non-negative')

    auto_crop = not any([left, right, top, bottom])
    if auto_crop:
        # Automatic cropping by masked pixels
        width = height = mask = None

        # Obtain the combined mask
        for file_id in job_file_ids:
            data = get_data_file_data(job.user_id, file_id)[0]
            if width is None:
                height, width = data.shape
            elif data.shape != (height, width):
                raise ValueError('All images must be of equal shapes')

            # Merge all masks
            if isinstance(data, np.ma.MaskedArray):
                if mask is None:
                    mask = data.mask.copy()
                else:
                    mask |= data.mask

        if mask is not None and mask.any():
            left, right, bottom, top = get_auto_crop(mask)

        if left + right >= width or bottom + top >= height:
            raise ValueError(
                'Empty crop for a {}x{} image: left={}, right={}, bottom={}, '
                'top={}'.format(width, height, left, right, bottom, top))

    if not any([left, right, bottom, top]) and inplace:
        # Nothing to do; if inplace=False, will simply duplicate all input
        # data files
        return job_file_ids

    # Crop all data files and adjust WCS
    new_file_ids = []
    for i, file_id in enumerate(job_file_ids):
        try:
            data, hdr = get_data_file_data(job.user_id, file_id)
            if any([left, right, bottom, top]):
                data = data[bottom:data.shape[0]-top, left:data.shape[1]-right]
                hdr.add_history(
                    '[{}] Cropped by Afterglow with margins: left={}, '
                    'right={}, bottom={}, top={}'
                    .format(datetime.utcnow(), left, right, bottom, top))

                # Move CRPIXn if present
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

                # Apply the original mask if any
                try:
                    mask = masks[file_id][bottom:bottom+data.shape[0],
                                          left:left+data.shape[1]]
                    if isinstance(data, np.ma.MaskedArray):
                        if data.mask.shape and data.mask.any():
                            data.mask |= mask
                        else:
                            data.mask = mask
                    else:
                        data = np.ma.masked_array(data, mask)
                except KeyError:
                    pass

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
                    with get_data_file_db(job.user_id) as adb:
                        try:
                            hdr.add_history(
                                'Original data file: {}'.format(
                                    get_data_file(
                                        job.user_id, file_id).name or
                                    file_id))
                            file_id = create_data_file(
                                adb, None, get_root(job.user_id), data, hdr,
                                duplicates='append',
                                session_id=job.session_id).id
                            adb.commit()
                        except Exception:
                            adb.rollback()
                            raise
            elif not inplace:
                # Merely duplicate the original data file
                with get_data_file_db(job.user_id) as adb:
                    try:
                        hdr.add_history(
                            'Original data file: {}'.format(
                                get_data_file(job.user_id, file_id).name or
                                file_id))
                        file_id = create_data_file(
                            adb, None, get_root(job.user_id), data, hdr,
                            duplicates='append', session_id=job.session_id).id
                        adb.commit()
                    except Exception:
                        adb.rollback()
                        raise

            new_file_ids.append(file_id)
        except Exception as e:
            job.add_error(e, {'file_id': job_file_ids[i]})
        finally:
            job.update_progress(
                (i + 1)/len(job_file_ids)*100, stage, total_stages)

    return new_file_ids


class CroppingSettings(AfterglowSchema):
    left: int = Integer(dump_default=0)
    right: int = Integer(dump_default=0)
    top: int = Integer(dump_default=0)
    bottom: int = Integer(dump_default=0)


class CroppingJobResult(JobResult):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class CroppingJob(Job):
    """
    Image cropping job
    """
    type = 'cropping'
    description = 'Crop Images'

    result: CroppingJobResult = Nested(CroppingJobResult, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: CroppingSettings = Nested(CroppingSettings, dump_default={})
    inplace: bool = Boolean(dump_default=False)

    def run(self):
        self.result.file_ids = run_cropping_job(
            self, self.settings, getattr(self, 'file_ids', []), self.inplace)
