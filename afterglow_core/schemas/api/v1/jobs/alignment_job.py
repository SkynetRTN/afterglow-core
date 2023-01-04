"""
Afterglow Core: image alignment job schemas
"""

from typing import List as TList, Optional

from marshmallow.fields import String, Integer, List, Nested

from .... import AfterglowSchema, Boolean, Float, NestedPoly
from ..job import JobSchema, JobResultSchema
from ..source_extraction import SourceExtractionDataSchema
from .source_extraction_job import SourceExtractionSettingsSchema


__all__ = ['AlignmentSettingsSchema', 'AlignmentJobResultSchema',
           'AlignmentJobSchema']


class AlignmentSettingsSchema(AfterglowSchema):
    __polymorphic_on__ = 'mode'

    mode: str = String(dump_default='WCS', load_default='WCS')
    ref_image: Optional[str] = String(dump_default='central', allow_none=True)
    mosaic_search_radius: float = Float(dump_default=1)
    prefilter: bool = Boolean(dump_default=True)
    enable_rot: bool = Boolean(dump_default=True)
    enable_scale: bool = Boolean(dump_default=True)
    enable_skew: bool = Boolean(dump_default=True)


class AlignmentSettingsWCSSchema(AlignmentSettingsSchema):
    mode = 'WCS'
    wcs_grid_points: int = Integer(dump_default=100)


class AlignmentSettingsSourcesSchema(AlignmentSettingsSchema):
    scale_invariant: bool = Boolean(dump_default=False)
    match_tol: float = Float(dump_default=0.002)
    min_edge: float = Float(dump_default=0.003)
    ratio_limit: float = Float(dump_default=10)
    confidence: float = Float(dump_default=0.15)


class AlignmentSettingsSourcesManualSchema(AlignmentSettingsSourcesSchema):
    mode = 'sources_manual'
    max_sources: int = Integer(dump_default=100)
    sources: TList[SourceExtractionDataSchema] = List(
        Nested(SourceExtractionDataSchema), dump_default=[])


class AlignmentSettingsSourcesAutoSchema(AlignmentSettingsSourcesSchema):
    mode = 'sources_auto'
    source_extraction_settings: Optional[SourceExtractionSettingsSchema] = \
        Nested(
            SourceExtractionSettingsSchema, allow_none=True, dump_default=None)


class AlignmentSettingsFeaturesSchema(AlignmentSettingsSchema):
    __polymorphic_on__ = 'algorithm'

    mode = 'features'

    algorithm: str = String(dump_default='WCS', load_default='AKAZE')
    ratio_threshold: float = Float(dump_default=0.5)
    detect_edges: bool = Boolean(dump_default=False)


class AlignmentSettingsFeaturesAKAZESchema(AlignmentSettingsFeaturesSchema):
    algorithm = 'AKAZE'
    descriptor_type: str = String(dump_default='MLDB')
    descriptor_size: int = Integer(dump_default=0)
    descriptor_channels: int = Integer(dump_default=3)
    threshold: float = Float(dump_default=0.001)
    octaves: int = Integer(dump_default=4)
    octave_layers: int = Integer(dump_default=4)
    diffusivity: str = String(dump_default='PM_G2')


class AlignmentSettingsFeaturesBRISKSchema(AlignmentSettingsFeaturesSchema):
    algorithm = 'BRISK'
    threshold: int = Integer(dump_default=30)
    octaves: int = Integer(dump_default=3)
    pattern_scale: float = Float(dump_default=1)


class AlignmentSettingsFeaturesKAZESchema(AlignmentSettingsFeaturesSchema):
    algorithm = 'KAZE'
    extended: bool = Boolean(dump_default=False)
    upright: bool = Boolean(dump_default=False)
    threshold: float = Float(dump_default=0.001)
    octaves: int = Integer(dump_default=4)
    octave_layers: int = Integer(dump_default=4)
    diffusivity: str = String(dump_default='PM_G2')


class AlignmentSettingsFeaturesORBSchema(AlignmentSettingsFeaturesSchema):
    algorithm = 'ORB'
    nfeatures: int = Integer(dump_default=500)
    scale_factor: float = Float(dump_default=1.2)
    nlevels: int = Integer(dump_default=8)
    edge_threshold: int = Integer(dump_default=31)
    first_level: int = Integer(dump_default=0)
    wta_k: int = Integer(dump_default=2)
    score_type: str = String(dump_default='Harris')
    patch_size: int = Integer(dump_default=31)
    fast_threshold: int = Integer(dump_default=20)


class AlignmentSettingsFeaturesSIFTSchema(AlignmentSettingsFeaturesSchema):
    algorithm = 'SIFT'
    nfeatures: int = Integer(dump_default=0)
    octave_layers: int = Integer(dump_default=3)
    contrast_threshold: float = Float(dump_default=0.04)
    edge_threshold: float = Float(dump_default=10)
    sigma: float = Float(dump_default=1.6)
    descriptor_type: str = String(dump_default='32F')


class AlignmentSettingsFeaturesSURFSchema(AlignmentSettingsFeaturesSchema):
    algorithm = 'SURF'
    hessian_threshold: float = Float(dump_default=100)
    octaves: int = Integer(dump_default=4)
    octave_layers: int = Integer(dump_default=3)
    extended: bool = Boolean(dump_default=False)
    upright: bool = Boolean(dump_default=False)


class AlignmentSettingsPixelsSchema(AlignmentSettingsSchema):
    mode = 'pixels'
    detect_edges: bool = Boolean(dump_default=False)


class AlignmentJobResultSchema(JobResultSchema):
    file_ids: TList[int] = List(Integer(), dump_default=[])


class AlignmentJobSchema(JobSchema):
    type = 'alignment'

    result: AlignmentJobResultSchema = Nested(
        AlignmentJobResultSchema, dump_default={})
    file_ids: TList[int] = List(Integer(), dump_default=[])
    settings: AlignmentSettingsSchema = NestedPoly(
        AlignmentSettingsSchema, dump_default={})
    inplace: bool = Boolean(dump_default=False)
    crop: bool = Boolean(dump_default=False)
