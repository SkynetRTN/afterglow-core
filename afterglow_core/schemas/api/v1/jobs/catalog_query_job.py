"""
Afterglow Core: catalog query job schemas
"""

from typing import List as TList

from marshmallow.fields import String, Integer, List, Nested, Dict

from .... import Float
from ..job import JobSchema, JobResultSchema
from ..catalog import CatalogSourceSchema


__all__ = ['CatalogQueryJobResultSchema', 'CatalogQueryJobSchema']


class CatalogQueryJobResultSchema(JobResultSchema):
    data = List(Nested(CatalogSourceSchema),
                default=[])  # type: TList[CatalogSourceSchema]


class CatalogQueryJobSchema(JobSchema):
    result = Nested(
        CatalogQueryJobResultSchema,
        default={})  # type: CatalogQueryJobResultSchema
    catalogs = List(String(), default=[])  # type: TList[str]
    ra_hours = Float()  # type: float
    dec_degs = Float()  # type: float
    radius_arcmins = Float()  # type: float
    width_arcmins = Float()  # type: float
    height_arcmins = Float()  # type: float
    file_ids = List(Integer())  # type: TList[int]
    constraints = Dict(keys=String, values=String)  # type: dict
    source_ids = List(String())  # type: TList[str]
