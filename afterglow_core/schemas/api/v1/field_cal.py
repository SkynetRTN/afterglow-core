"""
Afterglow Core: field calibration data structures
"""

from typing import List as TList

from marshmallow.fields import String, Integer, Dict, Nested, List

from ... import AfterglowSchema, Resource, Float
from .catalog import CatalogSourceSchema
from .photometry import PhotometryDataSchema


__all__ = ['FieldCalSchema', 'FieldCalResultSchema']


class FieldCalSchema(Resource):
    """
    Field calibration prescription
    """
    __get_view__ = 'field_cals'

    id = Integer()  # type: int
    name = String()  # type: str
    catalog_sources = List(
        Nested(CatalogSourceSchema))  # type: TList[CatalogSourceSchema]
    catalogs = List(String())  # type: list
    custom_filter_lookup = Dict(
        keys=String, values=Dict(keys=String, values=String))  # type: dict
    source_inclusion_percent = Float()  # type: float
    min_snr = Float()  # type: float
    max_snr = Float()  # type: float
    source_match_tol = Float()  # type: float


class FieldCalResultSchema(AfterglowSchema):
    """
    Result of field calibration for a data file
    """
    file_id = Integer()  # type: int
    phot_results = List(
        Nested(PhotometryDataSchema),
        default=[])  # type: TList[PhotometryDataSchema]
    zero_point = Float()  # type: float
    zero_point_error = Float()  # type: float
