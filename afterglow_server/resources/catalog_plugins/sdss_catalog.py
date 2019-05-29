"""
Afterglow Access Server: SDSS catalog
"""

from __future__ import absolute_import, division, print_function

from astropy.coordinates import SkyCoord
from astropy.units import deg, hour
from astroquery.sdss import SDSS

from .vizier_catalogs import VizierCatalog


__all__ = ['SDSSCatalog']


class SDSSCatalog(VizierCatalog):
    """
    SDSS/VizieR catalog plugin
    """
    name = 'SDSS'
    display_name = 'Sloan Digital Sky Survey Data Release 15'
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

    def query_objects(self, names):
        """
        Return a list of SDSS catalog objects with the specified names

        :param list[str] names: object names

        :return: list of catalog objects
        :rtype: list[afterglow_server.data_structures.CatalogSource]
        """
        sdss = SDSS()
        rows = []
        for name in names:
            rows.append(sdss.query_object(
                name, data_release=15, photoobj_fields=self._columns,
                cache=False)[0])
        return self.table_to_sources(rows)

    def query_region(self, ra_hours, dec_degs, constraints=None, limit=None,
                     **region):
        """
        Return SDSS catalog objects within the specified rectangular region

        :param float ra_hours: right ascension of region center in hours
        :param float dec_degs: declination of region center in degrees
        :param dict constraints: optional constraints on the column values
        :param int limit: maximum number of rows to return
        :param dict region: keywords defining the query region

        :return: list of catalog objects
        :rtype: list[afterglow_server.data_structures.CatalogSource]
        """
        sdss = SDSS()
        return self.table_to_sources(sdss.query_region(
            SkyCoord(ra=ra_hours, dec=dec_degs, unit=(hour, deg),
                     frame='icrs'),
            data_release=15, photoobj_fields=self._columns, cache=False,
            **region))
