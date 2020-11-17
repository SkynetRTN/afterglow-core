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
    name: str = String()
    catalog_sources: TList[CatalogSource] = List(Nested(CatalogSource))
    catalogs: TList[str] = List(String())
    custom_filter_lookup: TDict[str, TDict[str, str]] = Dict(
        keys=String, values=Dict(keys=String, values=String))
    source_inclusion_percent: float = Float()
    min_snr: float = Float()
    max_snr: float = Float()
    source_match_tol: float = Float()


class FieldCalResult(AfterglowSchema):
    """
    Result of field calibration for a data file
    """
    file_id: int = Integer()
    phot_results: TList[PhotometryData] = List(
        Nested(PhotometryData), default=[])
    zero_point: float = Float()
    zero_point_error: float = Float()
