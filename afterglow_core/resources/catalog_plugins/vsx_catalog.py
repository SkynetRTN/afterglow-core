"""
Afterglow Core: AAVSO International Variable Star indeX (VSX) interface
"""

from typing import List as TList, Union

from astropy.table import Table

from ...models import CatalogSource
from .vizier_catalogs import VizierCatalog


__all__ = ['VSXCatalog']


class VSXCatalog(VizierCatalog):
    """
    VSX/VizieR catalog plugin
    """
    name = 'VSX'
    display_name = 'AAVSO International Variable Star Index'
    num_sources = 2115593
    vizier_catalog = 'B/vsx/vsx'
    mags = {
        # Johnson broad-band
        'U': '', 'B': '', 'V': '', 'R': '', 'I': '',
        # Johnson infra-red (1.2, 1.6, 2.2, 3.5, 5µm)
        'J': '', 'H': '', 'K': '', 'L': '', 'M': '',
        # Cousins' red and infra-red
        'Rc': '', 'Ic': '',
        # Stroemgren intermediate-band
        'Su': '', 'Sv': '', 'Sb': '', 'Sy': '',
        # Sloan (SDSS)
        'uprime': '', 'gprime': '', 'rprime': '', 'iprime': '', 'zprime': '',
        # photographic blue (pg, bj) visual (pv), red (rf)
        'pg': '', 'pv': '', 'bj': '', 'rf': '',
        # white (clear); R or V used for comparison star.
        'w': '', 'C': '', 'CR': '', 'CV': '',
        # ROTSE-I (450-1000nm)
        'R1': '',
        # Hipparcos and Tycho (Cat. I/239)
        'Hp': '', 'T': '',
        # near-UV (Galex)
        'NUV': '',
        # STEREO mission filter (essentially 600-800nm)
        'H1A': '', 'H1B': '',
    }
    _mag_mapping = {  # n_max to Skynet filter names
        'u': 'Su', 'v': 'Sv', 'b': 'Sb', 'y': 'Sy',
        "u'": 'uprime', "g'": 'gprime', "r'": 'rprime', "i'": 'iprime',
        "z'": 'zprime',
    }
    extra_cols = [
        'OID', 'Name', 'V', 'Type', 'max', 'n_max', 'f_min', 'min', 'Period',
    ]

    def table_to_sources(self, table: Union[list, Table]) \
            -> TList[CatalogSource]:
        """
        Return a list of :class:`CatalogSource` objects from an Astropy table

        Converts color indices to magnitudes.

        :param table: table of sources returned by astroquery

        :return: list of catalog objects
        """
        sources = []
        for row in table:
            if row['V'] not in (0, 1):
                # Skip constant/non-existing/duplicates
                continue
            source = CatalogSource(
                catalog_name=self.name,
                id=row['OID'],
                name=row['Name'],
                type=row['Type'],
                mag=row['max'],
                amplitude=row['min'] if row['f_min'] == '('
                else row['min'] - row['max'],
                period=row['Period'] or None,
                ra_hours=row['RAJ2000']/15,
                dec_degs=row['DEJ2000'],
            )

            # Map mag to specific passband
            setattr(source, self._mag_mapping.get(row['n_max'], row['n_max']),
                    row['max'])

            sources.append(source)

        return sources
