"""
Afterglow Core: catalog query job schemas
"""

from marshmallow.fields import String, Integer, List, Nested, Dict

from .... import Float
from ..job import Job, JobResult
from ..field_cal import CatalogSource


__all__ = ['CatalogQueryJobResult', 'CatalogQueryJobSchema']


class CatalogQueryJobResult(JobResult):
    data = List(Nested(CatalogSource), default=[])  # type: list


class CatalogQueryJobSchema(Job):
    result = Nested(
        CatalogQueryJobResult, default={})  # type: CatalogQueryJobResult
    catalogs = List(String(), default=[])  # type: list
    ra_hours = Float()  # type: float
    dec_degs = Float()  # type: float
    radius_arcmins = Float()  # type: float
    width_arcmins = Float()  # type: float
    height_arcmins = Float()  # type: float
    file_ids = List(Integer())  # type: list
    constraints = Dict(keys=String, values=String)
    source_ids = List(String())  # type: list
