"""
Afterglow Core: APASS catalog accessed via VizieR
"""

from .vizier_catalogs import VizierCatalog


__all__ = ['APASSCatalog']


class APASSCatalog(VizierCatalog):
    """
    APASS/VizieR catalog plugin
    """
    name = 'APASS'
    display_name = 'AAVSO Photometric All Sky Survey Data Release 9'
    num_sources = 61176401
    vizier_catalog = 'II/336'
    row_limit = 1000
    mags = {
        'B': ('Bmag', 'e_Bmag'), 'V': ('Vmag', 'e_Vmag'),
        'gprime': ("g'mag", "e_g'mag"), 'rprime': ("r'mag", "e_r'mag"),
        'iprime': ("i'mag", "e_i'mag"),
    }
    col_mapping = {
        'id': 'recno', 'ra_hours': 'RAJ2000/15', 'dec_degs': 'DEJ2000',
    }
    filter_lookup = {
        # naming
        "g'": 'gprime', "r'": 'rprime', "i'": 'iprime',
        # Jester et al. (2005), Jordi et al. (2005)
        'U': 'B + 0.78*(uprime - gprime) - 0.88',
        # Lupton (2005)
        'R': "rprime - 0.2936*(rprime - iprime) - 0.1439",
        'I': "iprime - 0.3136*(rprime - iprime) - 0.3539",
    }
