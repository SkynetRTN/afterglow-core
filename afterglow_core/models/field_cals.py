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
    id = Integer()  # type: int
    name = String()  # type: str
    catalog_sources = List(Nested(CatalogSource))  # type: TList[CatalogSource]
    catalogs = List(String())  # type: list
    custom_filter_lookup = Dict(
        keys=String, values=Dict(
            keys=String, values=String))  # type: TDict[str, TDict[str, str]]
    source_inclusion_percent = Float()  # type: float
    min_snr = Float()  # type: float
    max_snr = Float()  # type: float
    source_match_tol = Float()  # type: float


class FieldCalResult(AfterglowSchema):
    """
    Result of field calibration for a data file
    """
    file_id = Integer()  # type: int
    phot_results = List(
        Nested(PhotometryData), default=[])  # type: TList[PhotometryData]
    zero_point = Float()  # type: float
    zero_point_error = Float()  # type: float
