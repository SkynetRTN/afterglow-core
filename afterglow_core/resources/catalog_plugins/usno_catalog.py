"""
Afterglow Core: USNO-B1.0 catalog accessed via VizieR
"""

from typing import List as TList, Union

from astropy.table import Table

from ...models import CatalogSource, Mag
from .vizier_catalogs import VizierCatalog


__all__ = ['USNOB1Catalog']


class USNOB1Catalog(VizierCatalog):
    """
    USNO-B1.0/VizieR catalog plugin
    """
    name = 'USNOB1'
    display_name = 'U.S. Naval Observatory Catalog of Astrometric Standards ' \
        '(USNO-B1.0)'
    num_sources = 1045175762
    vizier_catalog = 'I/284'
    row_limit = 5000
    mags = {
        'B': (), 'R': (), 'B1': ('B1mag',), 'B2': ('B2mag',), 'R1': ('R1mag',),
        'R2': ('R2mag',),
    }
    col_mapping = {
        'id': 'USNO-B1.0', 'ra_hours': 'RAJ2000/15', 'dec_degs': 'DEJ2000',
    }
    sort = ['+B1mag', '+B2mag', '+R1mag', '+R2mag']

    def table_to_sources(self, table: Union[list, Table]) \
            -> TList[CatalogSource]:
        """
        Return a list of CatalogSource objects from an Astropy table

        Adds the standard B and R magnitudes based on B1, B2 and R1, R2.

        :param table: table of sources returned by astroquery

        :return: list of catalog objects
        """
        sources = super(USNOB1Catalog, self).table_to_sources(table)

        for source in sources:
            mags = source.mags
            for m in ('B', 'R'):
                m1, m2 = m + '1', m + '2'
                try:
                    mags[m] = Mag(value=(mags[m1].value + mags[m2].value)/2)
                except (KeyError, ValueError):
                    try:
                        mags[m] = mags[m1]
                    except KeyError:
                        try:
                            mags[m] = mags[m2]
                        except KeyError:
                            pass

        return sources
