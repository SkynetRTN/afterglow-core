"""
Afterglow Core: image stacking job plugin
"""

from __future__ import absolute_import, division, print_function

from marshmallow.fields import Integer, List, Nested, String

from skylib.combine.stacking import combine

from . import Job, JobResult
from ..data_files import (
    create_data_file, get_data_file, get_data_file_db, get_root)
from ... import AfterglowSchema, Float


__all__ = ['StackingJob']


class StackingSettings(AfterglowSchema):
    mode = String(default='average')  # type: str
    scaling = String(default=None)  # type: str
    rejection = String(default=None)  # type: str
    percentile = Integer(default=50)  # type: int
    lo = Float(default=0)  # type: float
    hi = Float(default=100)  # type: float


class StackingJobResult(JobResult):
    file_id = Integer()  # type: int


class StackingJob(Job):
    name = 'stacking'
    description = 'Stack Images'
    result = Nested(StackingJobResult, default={})  # type: StackingJobResult
    file_ids = List(Integer(), default=[])  # type: list
    # alignment_settings = Nested(
    #     AlignmentSettings, default={})  # type: AlignmentSettings
    stacking_settings = Nested(
        StackingSettings, default={})  # type: StackingSettings

    def run(self):
        settings = self.stacking_settings

        if settings.mode not in ('average', 'sum', 'percentile', 'mode'):
            raise ValueError(
                'Stacking mode must be "average", "sum", "percentile", or '
                '"mode"')

        if settings.scaling is not None and \
                settings.scaling.lower() not in ('none', 'average', 'median',
                                                 'mode'):
            raise ValueError(
                'Stacking mode must be "none", "average", "median", or "mode"')
        if settings.scaling is not None:
            settings.scaling = settings.scaling.lower()
            if settings.scaling == 'none':
                settings.scaling = None

        if settings.rejection is not None and \
                settings.rejection.lower() not in ('none', 'chauvenet', 'iraf',
                                                   'minmax', 'sigclip'):
            raise ValueError(
                'Rejection mode must be "none", "chauvenet", "iraf", "minmax", '
                'or "sigclip"')
        if settings.rejection is not None:
            settings.rejection = settings.rejection.lower()
            if settings.rejection == 'none':
                settings.rejection = None

        lo, hi = settings.lo, settings.hi
        if settings.rejection == 'iraf':
            if lo is not None:
                if lo % 1:
                    raise ValueError(
                        'Number of lowest values to clip for rejection=iraf '
                        'must be integer')
                lo = int(lo)
            if hi is not None:
                if hi % 1:
                    raise ValueError(
                        'Number of highest values to clip for rejection=iraf '
                        'must be integer')
                hi = int(hi)

        # Load data files
        if not self.file_ids:
            return
        data_files = [get_data_file(self.user_id, file_id)
                      for file_id in self.file_ids]

        # Check data dimensions
        shape = data_files[0][0].shape
        for i, data_file in enumerate(list(data_files[1:])):
            if data_file[0].shape != shape:
                self.add_error(
                    'Data file {0} shape mismatch: expected {1[1]}x{1[0]}, got '
                    '{2[1]}x{2[0]}'.format(
                        self.file_ids[i + 1], shape, data_file[0].shape))
                data_files.remove(data_file)

        # Combine using the given settings
        fits = combine(
            data_files, mode=settings.mode, scaling=settings.scaling,
            rejection=settings.rejection, percentile=settings.percentile,
            lo=lo, hi=hi)

        # Create a new data file in the first input data file's session and
        # return its ID
        adb = get_data_file_db(self.user_id)
        try:
            self.result.file_id = create_data_file(
                adb, None, get_root(self.user_id), fits[0].data, fits[0].header,
                duplicates='append', session_id=self.session_id).id
            adb.commit()
        except Exception:
            adb.rollback()
            raise
