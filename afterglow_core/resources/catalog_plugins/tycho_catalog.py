"""
Afterglow Access Server: Tycho-2 catalog accessed via VizieR
"""

from __future__ import absolute_import, division, print_function

from .vizier_catalogs import VizierCatalog


__all__ = ['Tycho2Catalog']


class Tycho2Catalog(VizierCatalog):
    """
    Tycho-2/VizieR catalog plugin
    """
    name = 'Tycho2'
    display_name = 'Tycho-2 Main Catalog'
    num_sources = 2539913
    vizier_catalog = 'I/259'
    row_limit = 1000
    mags = {'B': ('BTmag', 'e_BTmag'), 'V': ('VTmag', 'e_VTmag')}
    col_mapping = {
        'id': '"{:04d}-{:05d}-{}".format(TYC1,TYC2,TYC3)',
        'ra_hours': 'RAmdeg/15', 'dec_degs': 'DEmdeg',
    }
