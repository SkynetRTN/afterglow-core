"""
Afterglow Core: SkyMapper catalog accessed via VizieR
"""

from typing import Dict as TDict, List as TList, Optional

from ...models import CatalogSource
from .vizier_catalogs import VizierCatalog


__all__ = ['SkyMapperCatalog']


class SkyMapperCatalog(VizierCatalog):
    """
    SkyMapper/VizieR catalog plugin
    """
    name = 'SkyMapper'
    display_name = 'SkyMapper Southern Sky Survey Data Release 1.1'
    num_sources = 285159194
    vizier_catalog = 'II/358/smss'
    row_limit = 5000
    col_mapping = {
        'id': 'ObjectId', 'ra_hours': 'RAICRS/15', 'dec_degs': 'DEICRS',
    }
    mags = {
        'u': ('uPSF', 'e_uPSF'), 'v': ('vPSF', 'e_vPSF'),
        'g': ('gPSF', 'e_gPSF'), 'r': ('rPSF', 'e_rPSF'),
        'i': ('iPSF', 'e_iPSF'), 'z': ('zPSF', 'e_zPSF'),
    }
    filter_lookup = {
        # See row F5V of the table at
        # https://skymapper.anu.edu.au/filter-transformations/
        'uprime': 'u - 0.069', 'gprime': 'g + 0.088', 'rprime': 'r - 0.006',
        'iprime': 'i + 0.001', 'zprime': 'z - 0.005',
    }

    def query_region(self, ra_hours: float, dec_degs: float,
                     constraints: Optional[TDict[str, str]] = None,
                     limit: int = None, **region) -> TList[CatalogSource]:
        """
        Return SkyMapper objects within the specified region

        :param ra_hours: right ascension of region center in hours
        :param dec_degs: declination of region center in degrees
        :param constraints: optional constraints on the column values;
            if unspecified, don't return stars with non-zero SExtractor flags
        :param limit: maximum number of rows to return
        :param region: keywords defining the query region

        :return: list of catalog objects within the specified region
        """
        if constraints is None:
            constraints = {}
        constraints.setdefault('flags', 0)
        return super().query_region(
            ra_hours, dec_degs, constraints, limit, **region)
