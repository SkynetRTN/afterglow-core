"""
Afterglow Core: catalog query job schemas
"""

from typing import Dict as TDict, List as TList

from marshmallow.fields import String, Integer, List, Nested, Dict

from .... import Float
from ..job import JobSchema, JobResultSchema
from ..catalog import CatalogSourceSchema


__all__ = ['CatalogQueryJobResultSchema', 'CatalogQueryJobSchema']


class CatalogQueryJobResultSchema(JobResultSchema):
    data: TList[CatalogSourceSchema] = List(
        Nested(CatalogSourceSchema), default=[])


class CatalogQueryJobSchema(JobSchema):
    type = 'catalog_query'

    result: CatalogQueryJobResultSchema = Nested(
        CatalogQueryJobResultSchema, default={})
    catalogs: TList[str] = List(String(), default=[])
    ra_hours: float = Float()
    dec_degs: float = Float()
    radius_arcmins: float = Float()
    width_arcmins: float = Float()
    height_arcmins: float = Float()
    file_ids: TList[int] = List(Integer())
    constraints: TDict[str, str] = Dict(keys=String, values=String)
    source_ids: TList[str] = List(String())
