"""
Afterglow Core: catalog plugin data model

A catalog plugin must subclass :class:`Catalog` and implement at
least its get_asset() and get_asset_data() methods.
"""

from typing import Dict as TDict, List as TList, Optional

from marshmallow.fields import Dict, Integer, List, Nested, String

from .. import app, errors
from ..schemas import AfterglowSchema
from .photometry import IPhotometry, Mag
from .source_extraction import IAstrometry


__all__ = ['Catalog', 'CatalogSource', 'ICatalogSource']


class ICatalogSource(AfterglowSchema):
    """
    Generic catalog source definition without astrometry
    """
    id: str = String()
    file_id: int = Integer()
    label: str = String()
    catalog_name: str = String()
    mags: TDict[str, Mag] = Dict(keys=String, values=Nested(Mag))


class CatalogSource(ICatalogSource, IAstrometry, IPhotometry):
    """
    Catalog source definition for field calibration
    """
    pass


class Catalog(AfterglowSchema):
    """
    Base class for catalog plugins

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
        query_objects: return a list of catalog objects with the specified
            names
        query_box: return catalog objects within the specified rectangular
            region
        query_circ: return catalog objects within the specified circular
            region
    """
    __polymorphic_on__ = 'name'

    name: str = String(default=None)
    display_name: str = String(default=None)
    num_sources: int = Integer()
    mags: TDict[str, TList[str]] = Dict(
        keys=String, values=List(String()), default={})
    filter_lookup: TDict[str, str] = Dict(keys=String, values=String)

    def __init__(self, **kwargs):
        """
        Create a Catalog instance

        :param kwargs: catalog-specific initialization parameters
        """
        # Override catalog option defaults with CATALOG_OPTIONS config var
        # for the current catalog
        kwargs = dict(kwargs)
        kwargs.update(app.config.get('CATALOG_OPTIONS', {}).get(self.name, {}))

        super().__init__(**kwargs)

        if self.display_name is None:
            self.display_name = self.name

    def query_objects(self, names: TList[str]) -> TList[CatalogSource]:
        """
        Return a list of catalog objects with the specified names

        :param names: object names

        :return: list of catalog objects with the specified names
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='query_objects')

    def query_box(self, ra_hours: float, dec_degs: float, width_arcmins: float,
                  height_arcmins: Optional[float] = None,
                  constraints: Optional[TDict[str, str]] = None,
                  limit: Optional[int] = None) \
            -> TList[CatalogSource]:
        """
        Return catalog objects within the specified rectangular region

        :param ra_hours: right ascension of region center in hours
        :param dec_degs: declination of region center in degrees
        :param width_arcmins: width of region in arcminutes
        :param height_arcmins: optional height of region in arcminutes;
            defaults to `width_arcmins`
        :param constraints: optional constraints on the column values
        :param limit: optional limit on the number of objects to return

        :return: list of catalog objects within the specified rectangular
            region
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='query_rect')

    def query_circ(self, ra_hours: float, dec_degs: float,
                   radius_arcmins: float,
                   constraints: Optional[TDict[str, str]] = None,
                   limit: Optional[int] = None) \
            -> TList[CatalogSource]:
        """
        Return catalog objects within the specified circular region

        :param ra_hours: right ascension of region center in hours
        :param dec_degs: declination of region center in degrees
        :param radius_arcmins: region radius in arcminutes
        :param constraints: optional constraints on the column values
        :param limit: optional limit on the number of objects to return

        :return: list of catalog objects
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='query_circ')
