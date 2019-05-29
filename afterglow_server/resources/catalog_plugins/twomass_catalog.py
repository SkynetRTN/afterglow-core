"""
Afterglow Access Server: 2MASS catalog accessed via VizieR
"""

from __future__ import absolute_import, division, print_function

from .vizier_catalogs import VizierCatalog


__all__ = ['TwoMASSCatalog']


class TwoMASSCatalog(VizierCatalog):
    """
    2MASS/VizieR catalog plugin
    """
    name = '2MASS'
    display_name = 'Two Micron All Sky Survey Catalog of Point Sources'
    num_sources = 470992970
    vizier_catalog = 'II/246'
    row_limit = 5000
    mags = {
        'J': ('Jmag', 'e_Jmag'), 'H': ('Hmag', 'e_Hmag'),
        'K': ('Kmag', 'e_Kmag'), 'B': ('Bmag',), 'R': ('Rmag',),
    }
    col_mapping = {
        'id': '_2MASS', 'ra_hours': 'RAJ2000/15', 'dec_degs': 'DEJ2000',
    }
    extra_cols = ['2MASS']  # VizieR returns "2MASS" as "_2MASS"
    filter_lookup = {
        'B': '0.1980 + J + (5.2150 + (-2.7785 + '
        '1.7495*(J - K))*(J - K))*(J - K)',
        'V': '0.1496 + J + (3.5143 + (-2.3250 + '
        '1.4688*(J - K))*(J - K))*(J - K)',
        'R': '0.1045 + J + (2.5105 + (-1.7849 + '
        '1.1230*(J - K))*(J - K))*(J - K)',
        'I': '0.0724 + J + (1.2816 + (-0.4866 + '
        '0.2963*(J - K))*(J - K))*(J - K)',
    }
