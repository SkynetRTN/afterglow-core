"""
Afterglow Core: field cal data model
"""

from typing import Dict as TDict, List as TList

from marshmallow.fields import Dict, Integer, List, Nested, String

from ..schemas import AfterglowSchema, Float
from .catalogs import CatalogSource
from .photometry import PhotometryData


__all__ = ['FieldCal', 'FieldCalResult']


class FieldCal(AfterglowSchema):
    """
    Field calibration prescription
    """
    id: int = Integer()
    user_id: int = Integer()
    name: str = String()
    catalog_sources: TList[CatalogSource] = List(Nested(CatalogSource))
    catalogs: TList[str] = List(String())
    custom_filter_lookup: TDict[str, TDict[str, str]] = Dict(keys=String, values=Dict(keys=String, values=String))
    source_inclusion_percent: float = Float()
    min_snr: float = Float()
    max_snr: float = Float()
    source_match_tol: float = Float()
    variable_check_tol: float = Float()
    max_star_rms: float = Float()
    max_stars: int = Integer()


class FieldCalResult(AfterglowSchema):
    """
    Result of field calibration for a data file
    """
    file_id: int = Integer()
    phot_results: TList[PhotometryData] = List(Nested(PhotometryData), dump_default=[])
    zero_point_corr: float = Float()
    zero_point_error: float = Float()
    zero_point_slop: float = Float()
    limmag5: float = Float()
    rej_percent: float = Float()
