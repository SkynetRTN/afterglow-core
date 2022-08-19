"""
Afterglow Core: SDSS catalog
"""

from typing import Dict as TDict, List as TList, Optional

import numpy as np
from astropy.coordinates import Angle, SkyCoord
from astropy.units import arcmin, arcsec, deg, hour
from astroquery.sdss import SDSSClass

from ...models import CatalogSource
from .vizier_catalogs import VizierCatalog


__all__ = ['SDSSCatalog']


class AfterglowSDSS(SDSSClass):
    """Generate SDSS SQL query specific to Afterglow"""
    def _args_to_payload(self, coordinates=None, radius=2*arcsec,
                         photoobj_fields=None, data_release=17, **kwargs):
        """Return the SQL query; see :meth:`SDSS._args_to_payload`"""
        if None in (coordinates, radius, photoobj_fields):
            return super()._args_to_payload(
                coordinates=None, radius=None, photoobj_fields=photoobj_fields,
                data_release=data_release, **kwargs)

        if isinstance(radius, tuple) and len(radius) == 2:
            # Rectangular region
            region = ''
            ra, dec = coordinates.ra.degree, coordinates.dec.degree
            h = Angle(radius[1]).to('degree').value/2
            dec_min, dec_max = dec - h, dec + h
            if dec_min < -90:
                # South Pole in FOV, use the whole RA range
                where = f's.dec <= {dec_max}'
            elif dec_max > 90:
                # North Pole in FOV, use the whole RA range
                where = f's.dec >= {dec_min}'
            else:
                w = np.rad2deg(np.arcsin(
                    np.sin(np.deg2rad(Angle(radius[0]).to('degree').value/2)) /
                    np.cos(np.deg2rad(dec))))
                ra_min, ra_max = ra - w, ra + w
                if ra_max >= ra_min + 360:
                    # RA spans the whole 360deg range
                    where = f's.dec BETWEEN {dec_min} AND {dec_max}'
                elif ra_min < 0:
                    # RA range encloses RA=0 => two separate RA ranges:
                    # ra_min + 360 <= ra <= 360 and 0 <= ra <= ra_max
                    where = f'(s.ra >= {ra_min + 360} OR s.ra <= {ra_max}) ' \
                        f'AND s.dec BETWEEN {dec_min} AND {dec_max}'
                elif ra_max > 360:
                    # RA range encloses RA=360 => two separate RA ranges:
                    # ra_min <= ra <= 360 and 0 <= ra <= ra_max - 360
                    where = f'(s.ra >= {ra_min} OR s.ra <= {ra_max - 360}) ' \
                        f'AND s.dec BETWEEN {dec_min} AND {dec_max}'
                else:
                    # RA range fully within [0, 24)
                    where = f's.ra BETWEEN {ra_min} AND {ra_max} ' \
                        f'AND s.dec BETWEEN {dec_min} AND {dec_max}'
        else:
            # Circular region
            region = 'fGetNearbyObjEq({},{},{}) AS n, '.format(
                coordinates.ra.degree, coordinates.dec.degree,
                Angle(radius).to('arcmin').value)
            where = 'n.objID = s.objID'

        # Construct SQL query
        # noinspection SqlResolve
        q = 'SELECT DISTINCT {} ' \
            'FROM {}Star AS s ' \
            'JOIN Field f ON s.fieldID = f.fieldID ' \
            'WHERE {} AND f.quality = 3 AND s.clean = 1' \
            .format(
                ', '.join(['s.{0}'.format(sql_field)
                           for sql_field in photoobj_fields]),
                region, where,
            )

        request_payload = dict(cmd=q, format='csv')

        if data_release > 11:
            request_payload['searchtool'] = 'SQL'

        return request_payload


SDSS = AfterglowSDSS()


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

    def query_box(self, ra_hours: float, dec_degs: float, width_arcmins: float,
                  height_arcmins: Optional[float] = None,
                  constraints: Optional[TDict[str, str]] = None,
                  limit: Optional[int] = None) \
            -> TList[CatalogSource]:
        """
        Return catalog objects within the specified rectangular region

        :param ra_hours: right ascension of region center in hours
        :param dec_degs: declination of region center in degrees
        :param width_arcmins: width of region in arcminutes
        :param height_arcmins: optional height of region in arcminutes;
            defaults to `width_arcmins`
        :param constraints: optional constraints on the column values
        :param limit: optional limit on the number of objects to return

        :return: list of catalog objects within the specified rectangular
            region
        """
        if height_arcmins is None:
            height_arcmins = width_arcmins

        if self.cache:
            ra_hours = round(ra_hours*5400)/5400 % 24
            dec_degs = round(dec_degs*360)/360
            if dec_degs > 90:
                dec_degs = 90
            elif dec_degs < -90:
                dec_degs = -90
            width_arcmins = np.ceil(width_arcmins*5)/5
            height_arcmins = np.ceil(height_arcmins*5)/5

        sdss = SDSS()
        return self.table_to_sources(sdss.query_region(
            SkyCoord(ra=ra_hours, dec=dec_degs, unit=(hour, deg),
                     frame='icrs'),
            radius=(width_arcmins*arcmin, height_arcmins*arcmin),
            photoobj_fields=self._columns, data_release=self.data_release,
            cache=self.cache))

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
                     frame='icrs'), radius=radius_arcmins*arcmin,
            photoobj_fields=self._columns, data_release=self.data_release,
            cache=self.cache))
