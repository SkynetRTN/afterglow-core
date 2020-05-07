"""
Afterglow Core: field calibration data structures
"""

import json

from marshmallow.fields import String, Integer, Dict, Nested, List

from . import AfterglowSchema, Resource, Float
from .photometry import Mag, IPhotometry, PhotometryData
from .source_extraction import IAstrometry


class ICatalogSource(AfterglowSchema):
    """
    Generic catalog source definition without astrometry
    """
    id = String()  # type: str
    file_id = Integer()  # type: int
    label = String()  # type: str
    catalog_name = String()  # type: str
    mags = Dict(keys=String, values=Nested(Mag))  # type: dict


class CatalogSource(ICatalogSource, IAstrometry, IPhotometry):
    """
    Catalog source definition for field calibration
    """
    pass


class FieldCal(Resource):
    """
    Field calibration prescription
    """
    id = Integer()  # type: int
    name = String()  # type: str
    catalog_sources = List(Nested(CatalogSource))  # type: list
    catalogs = List(String())  # type: list
    custom_filter_lookup = Dict(
        keys=String, values=Dict(keys=String, values=String))  # type: dict
    source_inclusion_percent = Float()  # type: float
    min_snr = Float()  # type: float
    max_snr = Float()  # type: float
    source_match_tol = Float()  # type: float

    @classmethod
    def from_db(cls, _obj=None, **kwargs):
        """
        Create field cal resource instance from database object

        :param afterglow_core.resources.field_cals.SqlaFieldCal _obj: field
            cal object returned by database query
        :param kwargs: if `_obj` is not set, initialize from the given
            keyword=value pairs or override `_obj` fields

        :return: serialized field cal resource object
        :rtype: FieldCal
        """
        # Extract fields from SQLA object
        if _obj is None:
            kw = {}
        else:
            # noinspection PyProtectedMember
            kw = {name: getattr(_obj, name) for name in cls._declared_fields
                  if hasattr(_obj, name)}
        kw.update(kwargs)

        # Convert fields stored as strings in the db to their proper schema
        # types
        for name in ('catalog_sources', 'catalogs', 'custom_filter_lookup'):
            if kw.get(name) is not None:
                kw[name] = json.loads(kw[name])

        return cls(**kw)


class FieldCalResult(AfterglowSchema):
    """
    Result of field calibration for a data file
    """
    file_id = Integer()  # type: int
    phot_results = List(Nested(PhotometryData), default=[])  # type: list
    zero_point = Float()  # type: float
    zero_point_error = Float()  # type: float


__all__ = [name for name, value in globals().items()
           if issubclass(value, AfterglowSchema)]
