"""
Afterglow Core: data provider schemas
"""

from marshmallow.fields import Dict, Integer, List, Nested, String

from ... import AfterglowSchema, Resource
from .photometry import MagSchema, IPhotometrySchema
from .source_extraction import IAstrometrySchema


__all__ = ['CatalogSchema', 'CatalogSourceSchema', 'ICatalogSourceSchema']


class CatalogSchema(Resource):
    """
    Catalog plugin schema

    Fields:
        name: unique catalog name
        display_name: more verbose catalog description; defaults to name
        num_sources: number of sources in the catalog
        mags: mapping between standard magnitude names like 'B', 'V', 'R' for
            magnitudes present in the catalog and catalog-specific magnitude
            names and errors; the value is a 0 to 2-element list: the first item
            is magnitude column name, the second item (if any) is magnitude
            error column name; empty list or null means that there is no direct
            correspondence to a catalog magnitude (e.g. if standard magnitudes
            are derived from catalog magnitudes using certain expressions);
            the mapping can be used to create catalog-specific constraint
            expressions
        filter_lookup: default custom mapping between certain bandpasses not
            present in the catalog and catalog magnitudes (in particular,
            aliases for non-standard catalog magnitude names), e.g. {'Open':
            '(3*B + 5*R)/8', "r'": 'rprime'}; used by field cal job
    """
    __polymorphic_on__ = 'name'
    __get_view__ = 'get_catalogs'

    name = String(default=None)
    display_name = String(default=None)
    num_sources = Integer()
    mags = Dict(keys=String, values=List(String()), default={})
    filter_lookup = Dict(keys=String, values=String)


class ICatalogSourceSchema(AfterglowSchema):
    """
    Generic catalog source definition without astrometry
    """
    id = String()  # type: str
    file_id = Integer()  # type: int
    label = String()  # type: str
    catalog_name = String()  # type: str
    mags = Dict(keys=String, values=Nested(MagSchema))  # type: dict


class CatalogSourceSchema(ICatalogSourceSchema, IAstrometrySchema,
                          IPhotometrySchema):
    """
    Catalog source definition for field calibration
    """
    pass
