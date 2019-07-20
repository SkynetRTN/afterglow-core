"""
Afterglow Access Server: image cropping job plugin
"""

from __future__ import absolute_import, division, print_function

from marshmallow.fields import Integer, List, Nested
from numpy.ma import MaskedArray

from ... import AfterglowSchema, Boolean, errors
from ..data_files import (
    SqlaDataFile, create_data_file, get_data_file, get_data_file_db, get_root,
    save_data_file)
from . import Job, JobResult


__all__ = ['CroppingJob']


class CroppingSettings(AfterglowSchema):
    left = Integer(default=0)  # type: int
    right = Integer(default=0)  # type: int
    top = Integer(default=0)  # type: int
    bottom = Integer(default=0)  # type: int


class CroppingJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: list


def max_rectangle(histogram):
    """
    Find left/right boundaries and height of the largest rectangle that fits
    entirely under the histogram; see https://gist.github.com/zed/776423

    :param array_like histogram: 1D non-negative integer array

    :return: left X coordinate, right X coordinate, and height of rectangle
    :rtype: tuple[int, int, int]
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


def get_auto_crop(user_id, file_ids):
    """
    Calculate optimal cropping margins for a set of masked images, e.g. after
    alignment

    :param int user_id: Afterglow user ID
    :param list file_ids: list of data file IDs

    :return: cropping margins (left, right, top, bottom)
    :rtype: tuple[float]
    """
    left = right = top = bottom = 0
    width = height = mask = None

    # Obtain the combined mask
    for file_id in file_ids:
        data = get_data_file(user_id, file_id)[0]
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


class CroppingJob(Job):
    """
    Image cropping job
    """
    name = 'cropping'
    description = 'Crop Images'
    result = Nested(CroppingJobResult, default={})  # type: CroppingJobResult
    file_ids = List(Integer(), default=[])  # type: list
    settings = Nested(CroppingSettings, default={})  # type: CroppingSettings
    inplace = Boolean(default=False)  # type: bool

    def run(self):
        if not getattr(self, 'file_ids'):
            return

        settings = self.settings
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
            raise errors.ValidationError(
                'settings.left', 'Left margin must be non-negative')
        if right < 0:
            raise errors.ValidationError(
                'settings.right', 'Right margin must be non-negative')
        if top < 0:
            raise errors.ValidationError(
                'settings.top', 'Top margin must be non-negative')
        if bottom < 0:
            raise errors.ValidationError(
                'settings.bottom', 'Bottom margin must be non-negative')

        auto_crop = not any([left, right, top, bottom])
        if auto_crop:
            # Automatic cropping by masked pixels
            left, right, top, bottom = get_auto_crop(
                self.user_id, self.file_ids)

        if not any([left, right, top, bottom]) and self.inplace:
            # Nothing to do; if inplace=False, will simply duplicate all input
            # data files
            return

        adb = get_data_file_db(self.user_id)

        # Crop all data files and adjust WCS
        for i, file_id in enumerate(self.file_ids):
            try:
                data, hdr = get_data_file(self.user_id, file_id)
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

                    if self.inplace:
                        # Overwrite the original data file
                        save_data_file(
                            get_root(self.user_id), file_id, data, hdr)

                        # Update image dimensions in the database
                        try:
                            data_file = adb.query(SqlaDataFile).get(file_id)
                            shape = data.shape
                            if shape != [data_file.height, data_file.width]:
                                data_file.height, data_file.width = shape
                                adb.commit()
                        except Exception:
                            adb.rollback()
                            raise
                    else:
                        hdr.add_history(
                            'Original data file ID: {:d}'.format(file_id))
                        try:
                            file_id = create_data_file(
                                adb, None, get_root(self.user_id), data, hdr,
                                duplicates='append',
                                session_id=self.session_id).id
                            adb.commit()
                        except Exception:
                            adb.rollback()
                            raise
                elif not self.inplace:
                    # Merely duplicate the original data file
                    try:
                        hdr.add_history(
                            'Original data file ID: {:d}'.format(file_id))
                        file_id = create_data_file(
                            adb, None, get_root(self.user_id), data, hdr,
                            duplicates='append', session_id=self.session_id).id
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
