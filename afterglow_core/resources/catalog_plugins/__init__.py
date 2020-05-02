"""
Afterglow Access Server: catalog plugin package

A catalog plugin must subclass :class:`Catalog` and implement at
least its get_asset() and get_asset_data() methods.
"""

from __future__ import absolute_import, division, print_function

from marshmallow.fields import Dict, Integer, List, String

from ... import Resource, app, errors
from ...data_structures import CatalogSource


__all__ = ['Catalog']


class Catalog(Resource):
    """
    Base class for JSON-serializable catalog plugins

    Plugin modules are placed in the :mod:`resources.catalog_plugins`
    subpackage and must directly or indirectly subclass from :class:`Catalog`,
    e.g.

    class MyCatalog(Catalog):
        name = 'my_catalog'
        num_sources = 1000000
        mags = {'B': ('Bmag', 'eBmag'), 'V': ('Vmag', 'eVmag'),
                'R': ('Rmag', 'eRmag'), 'I': ('Imag', 'eImag')}
        filter_lookup = {'Open': '(3*B + 5*R)/8'}

        def query_objects(self, names):  # optional
            ...

        def query_rect(self, ra_hours, dec_degs, width_arcmins, height_arcmins,
                       constraints=None):
            ...

        def query_circ(self, ra_hours, dec_degs, radius_arcmins,
                       constraints=None):
            ...

    Attributes::
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

    Methods::
        query_objects: return a list of catalog objects with the specified names
        query_box: return catalog objects within the specified rectangular
            region
        query_circ: return catalog objects within the specified circular
            region
    """
    __get_view__ = 'get_catalogs'

    name = String(default=None)
    display_name = String(default=None)
    num_sources = Integer()
    mags = Dict(keys=String, values=List(String()), default={})
    filter_lookup = Dict(keys=String, values=String)

    def __init__(self, *args, **kwargs):
        """
        Create a Catalog instance

        :param args: see :class:`afterglow_core.Resource`
        :param kwargs: see :class:`afterglow_core.Resource`
        """
        # Override catalog option defaults with CATALOG_OPTIONS config var
        # for the current catalog
        kwargs.update(app.config.get('CATALOG_OPTIONS', {}).get(self.name, {}))

        super(Catalog, self).__init__(*args, **kwargs)

        if self.display_name is None:
            self.display_name = self.name

    def query_objects(self, names):
        """
        Return a list of catalog objects with the specified names

        :param list[str] names: object names

        :return: list of catalog objects
        :rtype: list[CatalogSource]
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='query_objects')

    def query_box(self, ra_hours, dec_degs, width_arcmins, height_arcmins,
                  constraints=None):
        """
        Return catalog objects within the specified rectangular region

        :param float ra_hours: right ascension of region center in hours
        :param float dec_degs: declination of region center in degrees
        :param float width_arcmins: width of region in arcminutes
        :param float height_arcmins: height of region in arcminutes
        :param dict constraints: optional constraints on the column values

        :return: list of catalog objects
        :rtype: list[CatalogSource]
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='query_rect')

    def query_circ(self, ra_hours, dec_degs, radius_arcmins, constraints=None):
        """
        Return catalog objects within the specified circular region

        :param float ra_hours: right ascension of region center in hours
        :param float dec_degs: declination of region center in degrees
        :param float radius_arcmins: region radius in arcminutes
        :param dict constraints: optional constraints on the column values

        :return: list of catalog objects
        :rtype: list[CatalogSource]
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='query_circ')
