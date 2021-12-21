"""
Afterglow Core: VizieR catalog plugins
"""

import re
from typing import Dict as TDict, List as TList, Optional, Union

import numpy
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.units import arcmin, deg, hour
from astroquery import query
from astroquery.vizier import Vizier

from ... import app
from ...models import Catalog, CatalogSource, Mag


__all__ = ['VizierCatalog']


# Monkey-patch astroquery to not raise an exception if caching a query fails
# (e.g. due to concurrent access)
_to_cache = query.to_cache
_AstroQuery = query.AstroQuery


def to_cache(*args, **kwargs):
    # noinspection PyBroadException
    try:
        _to_cache(*args, **kwargs)
    except Exception:
        pass


class AstroQuery(_AstroQuery):
    def from_cache(self, *args, **kwargs):
        # noinspection PyBroadException
        try:
            return super().from_cache(*args, **kwargs)
        except Exception:
            pass

    def remove_cache_file(self, *args, **kwargs):
        # noinspection PyBroadException
        try:
            # noinspection PyUnresolvedReferences
            return super().remove_cache_file(*args, **kwargs)
        except Exception:
            pass


query.to_cache = to_cache
query.AstroQuery = AstroQuery


class VizierCatalog(Catalog):
    """
    Base class for VizieR catalog plugins

    Subclasses must define the following:

        name: unique Afterglow catalog name
        num_sources: number of sources in the catalog
        vizier_catalog: VizieR catalog ID, e.g. "II/246"
        row_limit: default limit on the number of rows to query
        col_mapping: mapping between :class:`CatalogObject` attributes
            and VizieR column names; the values are either column names as is
            (e.g. {'dec_degs': 'DEJ2000'}) or expressions involving these names
            and possibly any NumPy exports,
            e.g. {'some_attr': 'sqrt(some_col)'}
        extra_cols: optional extra column names that should be added to query
            arguments but don't map to any :class:`CatalogObject` attributes
    """
    vizier_server = None
    cache: bool = False
    vizier_catalog = None
    row_limit = None
    col_mapping = {'ra_hours': 'RAJ2000/15', 'dec_degs': 'DEJ2000'}
    extra_cols = []

    _columns = None

    def __init__(self, **kwargs):
        """
        Create a Catalog instance

        :param kwargs: catalog plugin initialization parameters
        """
        kwargs.setdefault('vizier_server', app.config.get(
            'VIZIER_SERVER',
            'https://vizier.cfa.harvard.edu/viz-bin/VizieR-4'))
        kwargs.setdefault('cache', app.config.get('VIZIER_CACHE', True))
        super().__init__(**kwargs)

        # Save the list of VizieR column names derived from column mapping
        # expressions and magnitude defs
        self._columns = []
        if self.col_mapping:
            for attrname, expr in self.col_mapping.items():
                try:
                    for name in compile(expr, '<string>', 'eval').co_names:
                        if name not in numpy.__dict__ and name not in dir(''):
                            self._columns.append(name)
                except SyntaxError:
                    # Columns that are not valid Python IDs or expressions
                    self._columns.append(expr)
                except ValueError as e:
                    # Bad column mapping expression
                    raise ValueError(
                        'Bad column definition "{}" for attribute "{}" of '
                        'catalog "{}": {}'
                        .format(expr, attrname, self.name, e))

        if self.extra_cols:
            self._columns += self.extra_cols

        if getattr(self, 'mags', None):
            for item in self.mags.values():
                try:
                    mag_col, mag_err_col = item[:2]
                except ValueError:
                    try:
                        mag_col, mag_err_col = item[0], None
                    except (IndexError, TypeError, ValueError):
                        continue
                if mag_col:
                    self._columns.append(mag_col)
                    if mag_err_col:
                        self._columns.append(mag_err_col)

    def table_to_sources(self, table: Union[TList, Table]) \
            -> TList[CatalogSource]:
        """
        Return a list of CatalogSource objects from an Astropy table

        :param table: table of sources returned by astroquery

        :return: list of catalog objects
        """
        sources = []

        context = dict(numpy.__dict__)

        for row in table:
            source = CatalogSource(catalog_name=self.name, mags={})

            # Map columns to CatalogObject attrs
            if self.col_mapping:
                for attr, expr in self.col_mapping.items():
                    try:
                        # Fast path
                        val = row[expr]
                    except KeyError:
                        ctx = dict(context)
                        ctx.update({name: row[name] for name in row.colnames})
                        # noinspection PyBroadException
                        try:
                            val = eval(expr, ctx, {})
                        except Exception:
                            val = None
                    if val is not None:
                        setattr(source, attr, val)

            # Initialize magnitudes and errors
            if getattr(self, 'mags', None):
                for mag, item in self.mags.items():
                    try:
                        mag_col, mag_err_col = item[:2]
                    except ValueError:
                        try:
                            mag_col, mag_err_col = item[0], None
                        except (IndexError, TypeError, ValueError):
                            continue
                    # noinspection PyBroadException
                    try:
                        val = row[mag_col.replace("'", '_')]
                        if val and val < 99:
                            m = Mag(value=val)
                            # noinspection PyBroadException
                            try:
                                val = row[mag_err_col.replace("'", '_')]
                                if val:
                                    m.error = val
                            except Exception:
                                pass
                            source.mags[mag] = m
                    except Exception:
                        # No such magnitude
                        pass

            if source.mags:
                sources.append(source)

        return sources

    def query_objects(self, names: TList[str]) -> TList[CatalogSource]:
        """
        Return a list of VizieR catalog objects with the specified names

        :param names: object names

        :return: list of catalog objects with the given names
        """
        kwargs = {}
        if self.vizier_server:
            kwargs['vizier_server'] = self.vizier_server
        viz = Vizier(
            catalog=self.vizier_catalog, columns=self._columns,
            row_limit=len(names), **kwargs)
        rows = []
        for name in names:
            resp = viz.query_object(
                name, catalog=viz.catalog, cache=self.cache)
            if resp:
                rows.append(resp[0][0])
        return self.table_to_sources(rows)

    def query_region(self, ra_hours: float, dec_degs: float,
                     constraints: Optional[TDict[str, str]] = None,
                     limit: int = None, **region) -> TList[CatalogSource]:
        """
        Return VizieR catalog objects within the specified region

        :param ra_hours: right ascension of region center in hours
        :param dec_degs: declination of region center in degrees
        :param constraints: optional constraints on the column values
        :param limit: maximum number of rows to return
        :param region: keywords defining the query region

        :return: list of catalog objects within the specified region
        """
        kwargs = {}
        if self.vizier_server:
            kwargs['vizier_server'] = self.vizier_server
        if not limit:
            limit = self.row_limit
        if limit:
            kwargs['row_limit'] = limit
        viz = Vizier(
            catalog=self.vizier_catalog, columns=self._columns,
            column_filters={name: val for name, val in constraints.items()
                            if val is not None} if constraints else {},
            keywords=[name for name, val in constraints.items() if val is None]
            if constraints else None,
            **kwargs)
        resp = viz.query_region(
            SkyCoord(ra=ra_hours, dec=dec_degs, unit=(hour, deg), frame='fk5'),
            catalog=viz.catalog, cache=self.cache, **region)
        if resp:
            return self.table_to_sources(resp[0])
        return []

    def query_box(self, ra_hours: float, dec_degs: float, width_arcmins: float,
                  height_arcmins: float = None,
                  constraints: Optional[TDict[str, str]] = None,
                  limit: Optional[int] = None) -> TList[CatalogSource]:
        """
        Return VizieR catalog objects within the specified rectangular region

        :param ra_hours: right ascension of region center in hours
        :param dec_degs: declination of region center in degrees
        :param width_arcmins: width of region in arcminutes
        :param height_arcmins: optional height of region in arcminutes;
            defaults to `width_arcmins`
        :param constraints: optional constraints on the column values
        :param limit: maximum number of rows to return

        :return: list of catalog objects within the specified rectangular
            region
        """
        return self.query_region(
            ra_hours, dec_degs, constraints, limit,
            width=width_arcmins*arcmin,
            height=(height_arcmins if height_arcmins
                    else width_arcmins)*arcmin)

    def query_circ(self, ra_hours: float, dec_degs: float,
                   radius_arcmins: float,
                   constraints: Optional[TDict[str, str]] = None,
                   limit: Optional[int] = None) -> TList[CatalogSource]:
        """
        Return catalog objects within the specified circular region

        :param ra_hours: right ascension of region center in hours
        :param dec_degs: declination of region center in degrees
        :param radius_arcmins: region radius in arcminutes
        :param constraints: optional constraints on the column values
        :param limit: maximum number of rows to return

        :return: list of catalog objects within the specified circular region
        """
        return self.query_region(
            ra_hours, dec_degs, constraints, limit,
            radius=radius_arcmins*arcmin)


# Load custom VizieR catalogs defined in the user's config
for kw in app.config.get('CUSTOM_VIZIER_CATALOGS', []):
    # noinspection PyBroadException
    try:
        # Generate Python class name from catalog name by removing all illegal
        # chars and prepending underscore to names starting with a digit

        classname = re.sub(
            r'(^\d)', r'_\1', re.sub(
                r'[^a-zA-z0-9_]', '', kw['name'])) + 'Catalog'
        newclass = type(classname, (VizierCatalog,), kw)
        newclass.__module__ = VizierCatalog.__module__
        globals()[classname] = newclass
        __all__.append(classname)
    except Exception:
        app.logger.warning(
            'Could not initialize custom VizieR catalog', exc_info=True)
