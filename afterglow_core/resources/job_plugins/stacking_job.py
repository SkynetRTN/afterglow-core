"""
Afterglow Core: image stacking job plugin
"""

from typing import List as TList, Optional

from marshmallow.fields import Integer, List, Nested, String
from flask import current_app

from skylib.combine.stacking import combine

from ...models import Job, JobResult
from ...schemas import AfterglowSchema, Boolean, Float
from ..data_files import (
    create_data_file, get_data_file_fits, get_data_file_db, get_root)


__all__ = ['StackingJob']


class StackingSettings(AfterglowSchema):
    mode: str = String(dump_default='average')
    percentile: float = Float(dump_default=50)
    scaling: str = String(dump_default=None)
    prescaling: str = String(dump_default=None)
    rejection: str = String(dump_default=None)
    lo: float = Float(dump_default=None)
    hi: float = Float(dump_default=None)
    propagate_mask: bool = Boolean(dump_default=True)
    equalize_additive: bool = Boolean(dump_default=False)
    equalize_order: int = Integer(dump_default=0)
    equalize_multiplicative: bool = Boolean(dump_default=False)
    multiplicative_percentile: float = Float(dump_default=99.9)
    equalize_global: bool = Boolean(dump_default=False)
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

        # TODO: Separate prescaling and scaling once implemented in AgA
        settings.prescaling = settings.scaling

        if settings.mode not in (
                'average', 'sum', 'median', 'percentile', 'mode'):
            raise ValueError(
                'Stacking mode must be "average", "sum", "median", '
                '"percentile", or "mode"')

        if settings.mode == 'percentile' and \
                not 0 <= settings.percentile <= 100:
            raise ValueError('Percentile value must be within 0 to 100')

        if settings.scaling is not None:
            settings.scaling = settings.scaling.lower()
            if settings.scaling not in (
                    'none', 'average', 'median', 'mode', 'histogram'):
                raise ValueError(
                    'Scaling mode must be "none", "average", "median", '
                    '"mode", or "histogram"')
            if settings.scaling == 'none':
                settings.scaling = None

        if settings.prescaling is not None:
            settings.prescaling = settings.prescaling.lower()
            if settings.prescaling not in (
                    'none', 'average', 'median', 'mode', 'histogram'):
                raise ValueError(
                    'Prescaling mode must be "none", "average", "median", '
                    '"mode", or "histogram"')
            if settings.prescaling == 'none':
                settings.prescaling = None

        if settings.rejection is not None:
            settings.rejection = settings.rejection.lower()
            if settings.rejection not in (
                    'none', 'chauvenet', 'iraf', 'minmax', 'sigclip', 'rcr'):
                raise ValueError(
                    'Rejection mode must be "none", "chauvenet", "rcr", '
                    '"iraf", "minmax", or "sigclip"')
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
                if lo != 0 and lo != 1:
                    raise ValueError(
                        'Negative clipping flag for rejection=chauvenet|rcr '
                        'must be 0 or 1')
                lo = bool(int(lo))
            if hi is not None:
                if hi != 0 and hi != 1:
                    raise ValueError(
                        'Positive clipping flag for rejection=chauvenet|rcr '
                        'must be 0 or 1')
                hi = bool(int(hi))

        if settings.smart_stacking:
            if settings.smart_stacking not in (
                    None, 'none', 'SNR', 'sharpness'):
                raise ValueError(
                    'Unsupported smart stacking mode "{}"'
                    .format(settings.smart_stacking))
            if settings.smart_stacking.lower() == 'none':
                settings.smart_stacking = None

        # Load data files
        if not self.file_ids:
            return
        data_files = [get_data_file_fits(self.user_id, file_id)
                      for file_id in self.file_ids]

        try:
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
                data_files, mode=settings.mode, percentile=settings.percentile,
                scaling=settings.scaling, prescaling=settings.prescaling,
                rejection=settings.rejection, lo=lo, hi=hi,
                propagate_mask=settings.propagate_mask,
                equalize_additive=settings.equalize_additive,
                equalize_order=settings.equalize_order,
                equalize_multiplicative=settings.equalize_multiplicative,
                multiplicative_percentile=settings.multiplicative_percentile,
                equalize_global=settings.equalize_global,
                smart_stacking=settings.smart_stacking,
                max_mem_mb=current_app.config.get('JOB_MAX_RAM'),
                callback=self.update_progress)[0]
        finally:
            for df in data_files:
                df.close()

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
