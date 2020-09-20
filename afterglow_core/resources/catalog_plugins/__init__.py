"""
Afterglow Core: catalog plugin package

A catalog plugin must subclass :class:`Catalog` and implement at
least its get_asset() and get_asset_data() methods.
"""

from __future__ import absolute_import, division, print_function

from ... import app, errors
from ...schemas.api.v1 import CatalogSchema

__all__ = ['Catalog']


class Catalog(CatalogSchema):
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

    Methods:
        query_objects: return a list of catalog objects with the specified names
        query_box: return catalog objects within the specified rectangular
            region
        query_circ: return catalog objects within the specified circular
            region
    """
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
