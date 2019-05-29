"""
Afterglow Access Server: UCAC5 catalog accessed via VizieR
"""

from __future__ import absolute_import, division, print_function

from .vizier_catalogs import VizierCatalog


__all__ = ['UCAC5Catalog']


class UCAC5Catalog(VizierCatalog):
    """
    UCAC5/VizieR catalog plugin
    """
    name = 'UCAC5'
    display_name = 'Fifth U.S. Naval Observatory CCD Astrograph Catalog'
    num_sources = 107758513
    vizier_catalog = 'I/340'
    row_limit = 5000
    mags = {
        'Open': ('f.mag',), 'G': ('Gmag',), 'R': ('Rmag',), 'J': ('Jmag',),
        'H': ('Hmag',), 'K': ('Kmag',),
    }
    col_mapping = {
        'id': 'SrcIDgaia', 'ra_hours': 'RAJ2000/15', 'dec_degs': 'DEJ2000',
    }
