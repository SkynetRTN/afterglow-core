"""
Afterglow Core: Landolt catalog of UBVRI photometric standards accessed
via VizieR
"""

from typing import List as TList, Union

from numpy import hypot, sqrt
from astropy.table import Table

from ...models import CatalogSource, Mag
from .vizier_catalogs import VizierCatalog


__all__ = ['LandoltCatalog']


class LandoltCatalog(VizierCatalog):
    """
    Landolt/VizieR catalog plugin
    """
    name = 'Landolt'
    display_name = 'Landolt Catalog of UBVRI Photometric Standards'
    num_sources = 526
    vizier_catalog = 'II/183A'
    mags = {
        'U': (), 'B': (), 'V': ('Vmag', 'e_Vmag'), 'R': (), 'I': (),
        'B_V': ('B-V', 'e_B-V'), 'U_B': ('U-B', 'e_U-B'),
        'V_R': ('V-R', 'e_V-R'), 'R_I': ('R-I', 'e_R-I'),
        'V_I': ('V-I', 'e_V-I'),
    }
    col_mapping = {
        'id': 'Star',
        'ra_hours': 'int(RAJ2000.split()[0]) + int(RAJ2000.split()[1])/60 + '
        'float(RAJ2000.split()[2])/3600',
        'dec_degs': '(abs(int(DEJ2000.split()[0])) + '
        'int(DEJ2000.split()[1])/60 + float(DEJ2000.split()[2])/3600)*'
        '(1 - 2*(DEJ2000.strip().startswith("-")))',
    }

    def table_to_sources(self, table: Union[list, Table]) \
            -> TList[CatalogSource]:
        """
        Return a list of :class:`CatalogSource` objects from an Astropy table

        Converts color indices to magnitudes.

        :param table: table of sources returned by astroquery

        :return: list of catalog objects
        """
        sources = super().table_to_sources(table)

        for source in sources:
            mags = source.mags
            v, v_err = mags['V'].value, getattr(mags['V'], 'error', 0)

            mags['B'] = Mag(value=v + mags['B_V'].value)
            err = hypot(v_err, getattr(mags['B_V'], 'error', 0))
            if err:
                mags['B'].error = err

            mags['U'] = Mag(value=mags['B'].value + mags['U_B'].value)
            err = hypot(getattr(mags['B'], 'error', 0),
                        getattr(mags['V_R'], 'error', 0))
            if err:
                mags['U'].error = err

            mags['R'] = Mag(value=v - mags['V_R'].value)
            err = hypot(v_err, getattr(mags['V_R'], 'error', 0))
            if err:
                mags['R'].error = err

            mags['I'] = Mag(
                value=(mags['R'].value - mags['R_I'].value +
                       v - mags['V_I'].value)/2)
            err = sqrt((getattr(mags['R'], 'error', 0)**2 +
                        getattr(mags['R_I'], 'error', 0)**2 +
                        v_err**2 + getattr(mags['V_I'], 'error', 0)**2)/2)
            if err:
                mags['I'].error = err

        return sources
