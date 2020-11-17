"""
Afterglow Core: image cropping job plugin
"""

from __future__ import annotations

from typing import List as TList, Optional, Tuple

from marshmallow.fields import Integer, List, Nested
from numpy import ndarray
from numpy.ma import MaskedArray

from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean
from ...errors import ValidationError
from ..data_files import (
    create_data_file, get_data_file_data, get_data_file_db, get_root,
    save_data_file)


__all__ = ['CroppingJob', 'run_cropping_job']


def max_rectangle(histogram: ndarray) -> Tuple[int, int, int]:
    """
    Find left/right boundaries and height of the largest rectangle that fits
    entirely under the histogram; see https://gist.github.com/zed/776423

    :param histogram: 1D non-negative integer array

    :return: left X coordinate, right X coordinate, and height of rectangle
    """
    stack = []
    left = right = height = pos = 0
    for pos, h in enumerate(histogram):
        start = pos
        while True:
            if not stack or h > stack[-1][1]:
                stack.append((start, h))
            elif stack and h < stack[-1][1]:
                top_start, top_height = stack[-1]
                if (pos - top_start + 1)*top_height > (right - left + 1)*height:
                    left, right, height = top_start, pos, top_height
                start = stack.pop()[0]
                continue
            break

    for start, h in stack:
        if (pos - start + 1)*h > (right - left + 1)*height:
            left, right, height = start, pos, h

    return left, right, height


def get_auto_crop(user_id: int, file_ids: TList[int]) \
        -> Tuple[float, float, float, float]:
    """
    Calculate optimal cropping margins for a set of masked images, e.g. after
    alignment

    :param int user_id: Afterglow user ID
    :param list file_ids: list of data file IDs

    :return: cropping margins (left, right, top, bottom)
    """
    left = right = top = bottom = 0
    width = height = mask = None

    # Obtain the combined mask
    for file_id in file_ids:
        data = get_data_file_data(user_id, file_id)[0]
        if width is None:
            height, width = data.shape
        elif data.shape != (height, width):
            raise ValueError('All images must be of equal shapes')

        # Merge masks for all images
        if isinstance(data, MaskedArray):
            if mask is None:
                mask = data.mask.copy()
            else:
                mask |= data.mask

    if mask is not None and mask.any():
        # Obtain the largest-area axis-aligned rectangle enclosed
        # in the non-masked area of the combined mask; the algorithm
        # is based on https://gist.github.com/zed/776423
        hist = (~(mask[0])).astype(int)
        left, right, rect_height = max_rectangle(hist)
        bottom = top = 0
        for i, row in enumerate(mask[1:]):
            hist[~row] += 1
            hist[row] = 0
            j1, j2, h = max_rectangle(hist)
            if (j2 - j1 + 1)*h > (right - left + 1)*rect_height:
                left, right, rect_height = j1, j2, h
                bottom, top = i + 2 - h, i + 1
        right = width - 1 - right
        top = height - 1 - top

    if left + right >= width or bottom + top >= height:
        raise ValueError(
            'Empty crop for a {}x{} image: left={}, right={}, top={}, '
            'bottom={}'.format(width, height, left, right, top, bottom))

    return left, right, top, bottom


def run_cropping_job(job: Job,
                     settings: Optional[CroppingSettings],
                     job_file_ids: TList[int],
                     inplace: bool = False) -> TList[int]:
    """
    Image cropping job body; also used during alignment

    :param job: job class instance
    :param settings: cropping settings
    :param job_file_ids: data file IDs to process
    :param inplace: crop in place instead of creating a new data file

    :return: list of generated/modified data file IDs
    """
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
        left, right, top, bottom = get_auto_crop(job.user_id, job_file_ids)

    if not any([left, right, top, bottom]) and inplace:
        # Nothing to do; if inplace=False, will simply duplicate all input
        # data files
        return job_file_ids

    adb = get_data_file_db(job.user_id)

    # Crop all data files and adjust WCS
    new_file_ids = []
    for i, file_id in enumerate(job_file_ids):
        try:
            data, hdr = get_data_file_data(job.user_id, file_id)
            if any([left, right, top, bottom]):
                if auto_crop and isinstance(data, MaskedArray):
                    # Automatic cropping guarantees that there are no masked
                    # pixels
                    data = data.data
                data = data[bottom:-(top + 1), left:-(right + 1)]
                hdr.add_history(
                    'Cropped with margins: left={}, right={}, top={}, '
                    'bottom={}'.format(left, right, top, bottom))

                # Move CRPIXn if present
                if left:
                    try:
                        hdr['CRPIX1'] -= left
                    except (KeyError, ValueError):
                        pass
                if bottom:
                    try:
                        hdr['CRPIX2'] -= bottom
                    except (KeyError, ValueError):
                        pass

                if inplace:
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
                    try:
                        file_id = create_data_file(
                            adb, None, get_root(job.user_id), data, hdr,
                            duplicates='append', session_id=job.session_id).id
                        adb.commit()
                    except Exception:
                        adb.rollback()
                        raise
            elif not inplace:
                # Merely duplicate the original data file
                try:
                    hdr.add_history(
                        'Original data file ID: {:d}'.format(file_id))
                    file_id = create_data_file(
                        adb, None, get_root(job.user_id), data, hdr,
                        duplicates='append', session_id=job.session_id).id
                    adb.commit()
                except Exception:
                    adb.rollback()
                    raise

            new_file_ids.append(file_id)
        except Exception as e:
            job.add_error('Data file ID {}: {}'.format(job_file_ids[i], e))
        finally:
            job.state.progress = (i + 1)/len(job_file_ids)*100
            job.update()

    return new_file_ids


class CroppingSettings(AfterglowSchema):
    left: int = Integer(default=0)
    right: int = Integer(default=0)
    top: int = Integer(default=0)
    bottom: int = Integer(default=0)


class CroppingJobResult(JobResult):
    file_ids: TList[int] = List(Integer(), default=[])


class CroppingJob(Job):
    """
    Image cropping job
    """
    type = 'cropping'
    description = 'Crop Images'

    result: CroppingJobResult = Nested(CroppingJobResult, default={})
    file_ids: TList[int] = List(Integer(), default=[])
    settings: CroppingSettings = Nested(CroppingSettings, default={})
    inplace: bool = Boolean(default=False)

    def run(self):
        self.result.file_ids = run_cropping_job(
            self, self.settings, getattr(self, 'file_ids', []), self.inplace)
