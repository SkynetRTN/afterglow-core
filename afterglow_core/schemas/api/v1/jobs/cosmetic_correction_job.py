"""
Afterglow Core: image cropping job schemas
"""

from typing import List as TList

from marshmallow.fields import Integer, List, Nested

from .... import AfterglowSchema, Boolean, Float
from ..job import JobSchema, JobResultSchema


__all__ = ['CosmeticCorrectionSettingsSchema',
           'CosmeticCorrectionJobResultSchema',
           'CosmeticCorrectionJobSchema']


class CosmeticCorrectionSettingsSchema(AfterglowSchema):
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


class CosmeticCorrectionJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class CosmeticCorrectionJobSchema(JobSchema):
    type = 'cosmetic'

    result: CosmeticCorrectionJobResultSchema = Nested(
        CosmeticCorrectionJobResultSchema, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: CosmeticCorrectionSettingsSchema = Nested(
        CosmeticCorrectionSettingsSchema, dump_default={})
    inplace: bool = Boolean(dump_default=True)
