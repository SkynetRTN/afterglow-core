"""
Afterglow Core: SDSS catalog
"""

from typing import Dict as TDict, List as TList, Optional

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.units import arcmin, deg, hour
from astroquery.sdss import SDSS

from ...models import CatalogSource
from .vizier_catalogs import VizierCatalog


__all__ = ['SDSSCatalog']


class SDSSCatalog(VizierCatalog):
    """
    SDSS catalog plugin
    """
    name = 'SDSS'
    data_release = 17
    display_name = f'Sloan Digital Sky Survey Data Release {data_release}'
    num_sources = 260562744
    row_limit = 5000
    col_mapping = {
        'id': 'objID', 'ra_hours': 'ra/15', 'dec_degs': 'dec',
    }
    mags = {
        'u': ('u', 'err_u'), 'g': ('g', 'err_g'), 'r': ('r', 'err_r'),
        'i': ('i', 'err_i'), 'z': ('z', 'err_z'),
    }
    filter_lookup = {
        'uprime': 'u',
        'gprime': 'g - 0.06*(g - r - 0.53)',
        'rprime': 'r - 0.035*(r - i - 0.21)',
        'iprime': 'i - 0.041*(r - i - 0.21)',
        'zprime': 'z + 0.03*(i - z - 0.09)',
        'U': 'g + 0.39*(g - r) + 0.78*(u - g) - 0.67',
        'B': 'u - 0.8116*(u - g) + 0.1313',
        'V': 'g - 0.5784*(g - r) - 0.0038',
        'R': 'r - 0.2936*(r - i) - 0.1439',
        'I': 'i - 0.378*(i - z) - 0.3974'
    }

    def query_objects(self, names: TList[str]) -> TList[CatalogSource]:
        """
        Return a list of SDSS catalog objects with the specified names

        :param names: object names

        :return: list of catalog objects with the specified names
        """
        sdss = SDSS()
        rows = []
        for name in names:
            rows.append(sdss.query_object(
                name, data_release=self.data_release,
                photoobj_fields=self._columns, cache=self.cache)[0])
        return self.table_to_sources(rows)

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
        if self.cache:
            ra_hours = round(ra_hours*5400)/5400 % 24
            dec_degs = round(dec_degs*360)/360
            if dec_degs > 90:
                dec_degs = 90
            elif dec_degs < -90:
                dec_degs = -90
            radius_arcmins = np.ceil(radius_arcmins*5)/5
        sdss = SDSS()
        return self.table_to_sources(sdss.query_region(
            SkyCoord(ra=ra_hours, dec=dec_degs, unit=(hour, deg),
                     frame='icrs'),
            data_release=self.data_release, photoobj_fields=self._columns,
            cache=self.cache, radius=radius_arcmins*arcmin))
