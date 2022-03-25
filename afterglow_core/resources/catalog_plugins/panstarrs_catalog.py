"""
Afterglow Core: PanSTARRS catalog accessed via VizieR
"""

from .vizier_catalogs import VizierCatalog


__all__ = ['PanSTARRSCatalog']


class PanSTARRSCatalog(VizierCatalog):
    """
    PanSTARRS/VizieR catalog plugin
    """
    name = 'PanSTARRS'
    display_name = 'Pan-STARRS Release 1 Survey Data Release 1'
    num_sources = 1919106885
    vizier_catalog = 'II/349'
    row_limit = 5000
    col_mapping = {
        'id': 'objID', 'ra_hours': 'RAJ2000/15', 'dec_degs': 'DEJ2000',
    }
    mags = {
        'g': ('gmag', 'e_gmag'), 'r': ('rmag', 'e_rmag'),
        'i': ('imag', 'e_imag'), 'z': ('zmag', 'e_zmag'),
        'y': ('ymag', 'e_ymag'),
    }
    sort = ['+rmag']
    filter_lookup = {
        # griz(P1) -> griz(SDSS) as per
        # https://iopscience.iop.org/article/10.1088/0004-637X/750/2/99
        # then the inverse of g'r'i'z' -> griz(SDSS) as per
        # http://classic.sdss.org/dr7/algorithms/jeg_photometric_eq_dr1.html
        # (see also sdss_catalog)
        'gprime': '0.94*(g + 0.013 + 0.145*(g - r) + 0.019*(g - r)**2) + '
        '0.06*(r - 0.001 + 0.004*(g - r) + 0.007*(g - r)**2) + 0.0318',
        'rprime': '0.965*(r - 0.001 + 0.004*(g - r) + 0.007*(g - r)**2) + '
        '0.035*(i - 0.005 + 0.011*(g - r) + 0.010*(g - r)**2) + 0.00735',
        'iprime': '1.041*(i - 0.005 + 0.011*(g - r) + 0.010*(g - r)**2) - '
        '0.041*(r - 0.001 + 0.004*(g - r) + 0.007*(g - r)**2) + 0.00861',
        'zprime': '0.97*(z + 0.013 - 0.039*(g - r) - 0.012*(g - r)**2) + '
        '0.03*(i - 0.005 + 0.011*(g - r) + 0.010*(g - r)**2) - 0.0027',
    }
