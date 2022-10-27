"""
Afterglow Core: image stacking job plugin
"""

from typing import List as TList, Optional

from marshmallow.fields import Integer, List, Nested, String

from skylib.combine.stacking import combine

from flask import current_app as app
from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean, Float
from ..data_files import (
    create_data_file, get_data_file_fits, get_data_file_db, get_root)


__all__ = ['StackingJob']


class StackingSettings(AfterglowSchema):
    mode: str = String(dump_default='average')
    scaling: str = String(dump_default=None)
    rejection: str = String(dump_default=None)
    propagate_mask: bool = Boolean(dump_default=True)
    percentile: int = Integer(dump_default=50)
    lo: float = Float(dump_default=0)
    hi: float = Float(dump_default=100)
    equalize_order: int = Integer(dump_default=1)
    smart_stacking: Optional[str] = String(dump_default=None)


class StackingJobResult(JobResult):
    file_id: int = Integer()


class StackingJob(Job):
    type = 'stacking'
    description = 'Stack Images'

    result: StackingJobResult = Nested(StackingJobResult, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    stacking_settings: StackingSettings = Nested(
        StackingSettings, dump_default={})

    def run(self):
        settings = self.stacking_settings

        if settings.mode not in ('average', 'sum', 'percentile', 'mode'):
            raise ValueError(
                'Stacking mode must be "average", "sum", "percentile", or '
                '"mode"')

        if settings.scaling is not None and \
                settings.scaling.lower() not in ('none', 'average', 'median',
                                                 'mode', 'equalize'):
            raise ValueError(
                'Scaling mode must be "none", "average", "median", "mode", or '
                '"equalize"')
        if settings.scaling is not None:
            settings.scaling = settings.scaling.lower()
            if settings.scaling == 'none':
                settings.scaling = None

        if settings.rejection is not None and \
                settings.rejection.lower() not in ('none', 'chauvenet', 'iraf',
                                                   'minmax', 'sigclip', 'rcr'):
            raise ValueError(
                'Rejection mode must be "none", "chauvenet", "rcr", "iraf", '
                '"minmax", or "sigclip"')
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
        elif settings.rejection in ('chauvenet', 'rcr'):
            if lo is not None:
                if lo not in (0, 1):
                    raise ValueError(
                        'Negative clipping flag for rejection=chauvenet|rcr '
                        'must be 0 or 1')
                lo = bool(int(lo))
            if hi is not None:
                if hi not in (0, 1):
                    raise ValueError(
                        'Positive clipping flag for rejection=chauvenet|rcr '
                        'must be 0 or 1')
                hi = bool(int(hi))

        if settings.smart_stacking and settings.smart_stacking not in (
                None, 'none', 'SNR'):
            raise ValueError(
                'Unsupported smart stacking mode "{}"'
                .format(settings.smart_stacking))
        if settings.smart_stacking and \
                settings.smart_stacking.lower() == 'none':
            settings.smart_stacking = None

        # Load data files
        if not self.file_ids:
            return
        data_files = [get_data_file_fits(self.user_id, file_id)
                      for file_id in self.file_ids]

        # Check data dimensions
        shape = (
            data_files[0][0].header['NAXIS1'],
            data_files[0][0].header['NAXIS2']
        )
        for i, data_file in enumerate(list(data_files[1:])):
            if (data_file[0].header['NAXIS1'],
                    data_file[0].header['NAXIS2']) != shape:
                self.add_error(
                    ValueError(
                        'Shape mismatch: expected {0[0]}x{0[1]}, got '
                        '{1[0]}x{1[1]}'.format(shape, data_file[0].shape)),
                    {'file_id': self.file_ids[i + 1]})
                data_files.remove(data_file)

        # Combine using the given settings
        data, header = combine(
            data_files, mode=settings.mode, scaling=settings.scaling,
            rejection=settings.rejection,
            propagate_mask=settings.propagate_mask,
            percentile=settings.percentile,
            lo=lo, hi=hi, smart_stacking=settings.smart_stacking,
            equalize_order=settings.equalize_order,
            max_mem_mb=app.config.get('JOB_MAX_RAM'),
            callback=self.update_progress)[0]

        # Create a new data file in the given session and return its ID
        with get_data_file_db(self.user_id) as adb:
            try:
                self.result.file_id = create_data_file(
                    adb, None, get_root(self.user_id), data, header,
                    duplicates='append', session_id=self.session_id).id
                adb.commit()
            except Exception:
                adb.rollback()
                raise
