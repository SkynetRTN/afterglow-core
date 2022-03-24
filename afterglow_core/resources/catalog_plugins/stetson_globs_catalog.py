"""
Afterglow Core: UBVRI photometry in 48 globular clusters (Stetson+, 2019)
accessed via VizieR
"""

from .vizier_catalogs import VizierCatalog


__all__ = ['StetsonGlobsCatalog']


class StetsonGlobsCatalog(VizierCatalog):
    """
    Stetson's globular cluster photometry catalog plugin
    """
    name = 'Photometry of Globular Clusters'
    display_name = 'UBVRI photometry in 48 globular clusters (Stetson+, 2019)'
    num_sources = 4890955
    vizier_catalog = 'J/MNRAS/485/3042/table4'
    col_mapping = {
        'id': 'Star',
        'ra_hours': 'int(RAJ2000.split()[0]) + int(RAJ2000.split()[1])/60 + '
        'float(RAJ2000.split()[2])/3600',
        'dec_degs': '(abs(int(DEJ2000.split()[0])) + '
        'int(DEJ2000.split()[1])/60 + float(DEJ2000.split()[2])/3600)*'
        '(1 - 2*(DEJ2000.split()[0].startswith("-")))',
    }
    mags = {
        'U': ('Umag', 'e_Umag'), 'B': ('Bmag', 'e_Bmag'),
        'V': ('Vmag', 'e_Vmag'), 'R': ('Rmag', 'e_Rmag'),
        'I': ('Imag', 'e_Imag'),
    }
