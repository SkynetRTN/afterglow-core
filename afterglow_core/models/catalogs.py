"""
Afterglow Core: catalog plugin data model

A catalog plugin must subclass :class:`Catalog` and implement at
least its get_asset() and get_asset_data() methods.
"""

from typing import Dict as TDict, List as TList, Optional

import numpy as np
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
        filter_lookup = {'Open': '(3*B + 5*R)/8', '*': 'R'}
        # '*' stands for "use this for any unknown filter"

        def query_objects(self, names):  # optional
            ...

        def query_box(self, ra_hours, dec_degs, width_arcmins, height_arcmins,
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

    name: str = String(dump_default=None)
    display_name: str = String(dump_default=None)
    num_sources: int = Integer()
    mags: TDict[str, TList[str]] = Dict(
        keys=String, values=List(String()), dump_default={})
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

        Default implementation relies on :meth:`query_circ`.

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
        # Query the enclosing circular region
        try:
            stars = self.query_circ(
                ra_hours, dec_degs, np.hypot(width_arcmins, height_arcmins)/2,
                constraints, limit)
        except NotImplementedError:
            raise errors.MethodNotImplementedError(
                class_name=self.__class__.__name__, method_name='query_box')

        # Keep only stars within the specified rectangular region
        h = height_arcmins/120
        dec_min, dec_max = dec_degs - h, dec_degs + h
        if dec_min < -90:
            # South Pole in FOV, use the whole RA range
            stars = [s for s in stars if s.dec_degs <= dec_max]
        elif dec_max > 90:
            # North Pole in FOV, use the whole RA range
            stars = [s for s in stars if s.dec_degs >= dec_min]
        else:
            # See http://janmatuschek.de/LatitudeLongitudeBoundingCoordinates
            dra = np.rad2deg(np.arcsin(np.sin(np.deg2rad(width_arcmins/60)) /
                                       np.cos(np.deg2rad(dec_degs))))/15
            ra_min, ra_max = ra_hours - dra, ra_hours + dra
            if ra_max >= ra_min + 24:
                # RA spans the whole 24h range
                stars = [s for s in stars if dec_min <= s.dec_degs <= dec_max]
            elif ra_min < 0:
                # RA range encloses RA=0 => two separate RA ranges:
                # ra_min + 24 <= ra <= 24 and 0 <= ra <= ra_max
                stars = [s for s in stars
                         if (s.ra_hours >= ra_min + 24 or s.ra_hours <= ra_max)
                         and dec_min <= s.dec_degs <= dec_max]
            elif ra_max > 24:
                # RA range encloses RA=24 => two separate RA ranges:
                # ra_min <= ra <= 24 and 0 <= ra <= ra_max - 24
                stars = [s for s in stars
                         if (s.ra_hours >= ra_min or s.ra_hours <= ra_max - 24)
                         and dec_min <= s.dec_degs <= dec_max]
            else:
                # RA range fully within [0, 24)
                stars = [s for s in stars
                         if ra_min <= s.ra_hours <= ra_max
                         and dec_min <= s.dec_degs <= dec_max]

        return stars

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
