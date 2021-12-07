"""
Afterglow Core: field calibration data structures
"""

from typing import Dict as TDict, List as TList

from marshmallow.fields import String, Integer, Dict, Nested, List

from ... import AfterglowSchema, Float, Resource
from .catalog import CatalogSourceSchema
from .photometry import PhotometryDataSchema


__all__ = ['FieldCalSchema', 'FieldCalResultSchema']


class FieldCalSchema(Resource):
    """
    Field calibration prescription
    """
    __get_view__ = 'field_cals'

    id: int = Integer()
    name: str = String()
    catalog_sources: TList[CatalogSourceSchema] = List(
        Nested(CatalogSourceSchema))
    catalogs: TList[str] = List(String())
    custom_filter_lookup: TDict[str, TDict[str, str]] = Dict(
        keys=String, values=Dict(keys=String, values=String))
    source_inclusion_percent: float = Float()
    min_snr: float = Float()
    max_snr: float = Float()
    source_match_tol: float = Float()
    variable_check_tol: float = Float()
    max_star_rms: float = Float()
    max_stars: int = Integer()


class FieldCalResultSchema(AfterglowSchema):
    """
    Result of field calibration for a data file
    """
    file_id: int = Integer()
    phot_results: TList[PhotometryDataSchema] = List(
        Nested(PhotometryDataSchema), default=[])
    zero_point: float = Float()
    zero_point_error: float = Float()
