"""
Afterglow Core: imaging survey data provider plugin
"""

from typing import List as TList, Optional, Tuple, Union
from io import BytesIO

from marshmallow.fields import String
from marshmallow.validate import OneOf, Range
import requests
import astropy.io.fits as pyfits

from ...models import DataProvider, DataProviderAsset
from ...schemas import Float
from ...errors import MissingFieldError, ValidationError
from ...errors.data_provider import AssetNotFoundError


__all__ = ['DSSImageDataProvider']


class DSSImageDataProvider(DataProvider):
    r"""
    DSS image data provider plugin class

    Asset path is <ra>,<dec>\<width>,<height> or <ra>,<dec>\<width>

    where <ra> and <dec> are field center coordinates in degrees, <width> and
    <height> is FOV size in arcminutes (<height> = <width> if omitted), e.g.
    "1.234,+5.678\15.0".
    """
    name = 'dss'
    display_name = 'DSS Images'
    description = 'Access to Digitized Sky Survey images'
    searchable = True
    browseable = False
    readonly = True
    quota = usage = None
    allow_multiple_instances = False

    search_fields = dict(
        ra_hours=dict(
            label='Center RA', type='float', min_val=0,
            max_val=24),
        dec_degs=dict(
            label='Center Dec', type='float',
            min_val=-90, max_val=90),
        object=dict(label='Object', type='text'),
        width=dict(
            label='Field Width [arcmin]', type='float', min_val=0),
        height=dict(
            label='Field Height [arcmin]', type='int', min_val=0),
    )

    server: str = String(
        validate=OneOf(['STScI', 'ESO']), dump_default='STScI')
    timeout: float = Float(
        validate=Range(min=0, min_inclusive=False), dump_default=30)

    @staticmethod
    def _get_asset_params(path: str) -> Tuple[float, float, float, float]:
        r"""
        Decompose asset path into RA/Dec in degrees and field width/height
        in arcminutes

        :param path: asset path in the form <ra>,<dec>\<width>,<height>

        :return: tuple (RA, Dec, width, height)
        """
        try:
            position, size = path.split('\\')
            ra_degs, dec_degs = position.split(',')
            ra_degs, dec_degs = float(ra_degs), float(dec_degs)
            if not 0 <= ra_degs < 360:
                raise ValueError('Expected 0 <= ra < 360')
            if not -90 <= dec_degs <= 90:
                raise ValueError('Expected -90 <= dec <= 90')
            if ',' in size:
                width, height = size.split(',')
                width, height = float(width), float(height)
            else:
                width = height = float(size)
            if width <= 0:
                raise ValueError('Positive FOV width expected')
            if height <= 0:
                raise ValueError('Positive FOV height expected')
        except (TypeError, ValueError) as e:
            raise ValidationError('path', str(e))

        return ra_degs, dec_degs, width, height

    @staticmethod
    def _get_asset(ra_degs: float, dec_degs: float, width: float,
                   height: float) -> DataProviderAsset:
        """
        Return image survey data provider asset for the given parameters

        :param ra_degs: right ascension of field center in degrees
        :param dec_degs: declination of field center in degrees
        :param width: field width in arcminutes
        :param height: field height in arcminutes

        :return: asset object
        """
        if width == height:
            size = str(width)
        else:
            size = '{},{}'.format(width, height)
        return DataProviderAsset(
            name='DSS_{},{}'.format(ra_degs, dec_degs),
            collection=False,
            path='{},{}\\{}'.format(ra_degs, dec_degs, size),
            metadata={
                'type': 'FITS', 'survey': 'DSS',
                'ra': ra_degs, 'dec': dec_degs,
                'fov_ra': width, 'fov_dec': height,
                'layers': 1,
            },
        )

    def find_assets(self, path: Optional[str] = None,
                    sort_by: Optional[str] = None,
                    page_size: Optional[int] = None,
                    page: Optional[Union[int, str]] = None,
                    ra_hours: Optional[float] = None,
                    dec_degs: Optional[float] = None,
                    width: Optional[float] = None,
                    height: Optional[float] = None) \
            -> Tuple[TList[DataProviderAsset], None]:
        """
        Return a list of assets matching the given parameters

        Returns an empty list if survey is unknown or no imaging data at the
        given FOV; otherwise, returns a single asset

        :param path: path to the collection asset to search in; ignored
        :param sort_by: unused
        :param page_size: unused
        :param page: unused
        :param ra_hours: RA of image center in hours
        :param dec_degs: Dec of image center in degrees
        :param width: image width in arcminutes
        :param height: image height in arcminutes; default: same as `width`

        :return: list of 0 or 1 :class:`DataProviderAsset` objects for assets
            matching the query parameters, and None for the pagination info
        """
        if ra_hours is None:
            raise MissingFieldError('ra_hours')
        try:
            ra_hours = float(ra_hours)
            if not 0 <= ra_hours < 24:
                raise ValueError()
        except ValueError:
            raise ValidationError(
                'ra_hours', 'Expected 0 <= ra_hours < 24')

        if dec_degs is None:
            raise MissingFieldError('dec_degs')
        try:
            dec_degs = float(dec_degs)
            if not -90 <= dec_degs <= 90:
                raise ValueError()
        except ValueError:
            raise ValidationError(
                'dec_degs', 'Expected -90 <= dec_degs <= 90')

        if width is None and height is None:
            raise MissingFieldError('width,height')
        if width is not None:
            try:
                width = float(width)
                if width <= 0:
                    raise ValueError()
            except ValueError:
                raise ValidationError('width', 'Positive FOV width expected')
        if height is not None:
            try:
                height = float(height)
                if height <= 0:
                    raise ValueError()
            except ValueError:
                raise ValidationError('height', 'Positive FOV height expected')
        if width is None:
            width = height
        elif height is None:
            height = width

        return [self._get_asset(ra_hours*15, dec_degs, width, height)], None

    def get_asset(self, path: str) -> DataProviderAsset:
        r"""
        Return an asset at the given path

        :param path: asset path in the form
            <survey>\<position>\<width>,<height>

        :return: asset object
        """
        return self._get_asset(*self._get_asset_params(path))

    def get_asset_data(self, path: str) -> bytes:
        """
        Return data for a non-collection asset at the given path

        :param path: asset path; must identify a non-collection asset

        :return: asset data
        """
        ra_degs, dec_degs, width, height = self._get_asset_params(path)
        try:
            if self.server == 'STScI':
                url = 'https://archive.stsci.edu/cgi-bin/dss_search'
                params = {
                    'v': 'poss2ukstu_red',
                    'r': str(ra_degs),
                    'd': str(dec_degs),
                    'e': 'J2000',
                    'h': str(height),
                    'w': str(width),
                    'f': 'fits',
                    'c': 'none',
                    'fov': 'NONE',
                    'v3': '',
                }
            else:
                url = 'https://archive.eso.org/dss/dss/image'
                params = {
                    'ra': str(ra_degs),
                    'dec': str(dec_degs),
                    'equinox': 'J2000',
                    'name': '',
                    'x': str(width),
                    'y': str(height),
                    'Sky-Survey': 'DSS2-red',
                    'mime-type': 'download-fits',
                    'statsmode': 'WEBFORM',
                }

            res = requests.request(
                'GET', url, params=params, timeout=self.timeout)
        except Exception as e:
            raise AssetNotFoundError(path=path, reason=str(e))

        if res.status_code != 200:
            raise AssetNotFoundError(
                path=path,
                reason='Request failed (HTTP status {})'
                .format(res.status_code))

        buf = BytesIO(res.content)
        with pyfits.open(buf, 'readonly') as f:
            if len(f) > 1:
                try:
                    # Remove extension HDU
                    out = BytesIO()
                    f[0].writeto(out, output_verify='silentfix+ignore')
                    return out.getvalue()
                finally:
                    del f[0].data
        return res.content
