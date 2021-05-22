"""
Afterglow Core: imaging survey data provider plugin
"""

from typing import List as TList, Optional, Tuple

from io import BytesIO
from threading import Lock

from astropy import units as u
from astropy.coordinates import Angle
from astroquery.skyview import SkyView

from ...models import DataProvider, DataProviderAsset
from ...errors import MissingFieldError, ValidationError
from ...errors.data_provider import AssetNotFoundError
from ..imaging_surveys import survey_scales


__all__ = ['ImagingSurveyDataProvider']


class ImagingSurveyDataProvider(DataProvider):
    r"""
    Imaging survey data provider plugin class

    Asset path is <survey>\<position>\<width>,<height>

    where <survey> is survey name, <position> is field center coordinates or
    object name, <width> and <height> is FOV size in arcminutes, e.g.
    "DSS\Eta Carinae\30,20".
    """
    name = 'imaging_surveys'
    display_name = 'Imaging Surveys'
    description = 'Access to about 200 imaging surveys like DSS'
    searchable = True
    browseable = False
    readonly = True
    quota = usage = None
    allow_multiple_instances = False

    _search_fields: dict = None
    _search_fields_lock: Lock = None

    def __init__(self, **kwargs):
        """
        Create data provider instance

        :param kwargs: data provider initialization parameters; unused
        """
        super().__init__(**kwargs)
        self._search_fields_lock = Lock()

    @property
    def search_fields(self):
        """Dictionary of searchable fields"""
        with self._search_fields_lock:
            if self._search_fields is None:
                # Initialize search field dict on first access to prevent from
                # connecting to SkyView when importing the module, even if this
                # data provider is not enabled in the configuration
                # noinspection PyProtectedMember
                self._search_fields = dict(
                    survey=dict(
                        label='Survey', type='multi_choice',
                        enum=SkyView._valid_surveys),
                    ra_hours=dict(
                        label='Center RA', type='float', min_val=0, max_val=24),
                    dec_degs=dict(
                        label='Center Dec', type='float',
                        min_val=-90, max_val=90),
                    object=dict(label='Object', type='text'),
                    width=dict(
                        label='Field Width [arcmin]', type='float', min_val=0),
                    height=dict(
                        label='Field Height [arcmin]', type='int', min_val=0),
                )
            return self._search_fields

    @staticmethod
    def _get_asset_params(path: str) -> Tuple[str, str, float, float]:
        r"""
        Decompose asset path into SkyView-specific parameters: survey name,
        position/coordinates, and field width/height in arcminutes

        :param path: asset path in the form
            <survey>\<position>\<width>,<height>

        :return: tuple (survey, position, width, height)
        """
        try:
            survey, position, size = path.split('\\')
            if ',' in size:
                width, height = size.split(',')
                width, height = float(width), float(height)
            else:
                width = height = float(size)
        except (TypeError, ValueError):
            raise AssetNotFoundError(path=path)
        return survey, position, width, height

    @staticmethod
    def _get_asset(survey: str, position: str, width: float, height: float) \
            -> DataProviderAsset:
        """
        Return image survey data provider asset for the given parameters

        :param survey: survey name
        :param position: field center coordinates or object name
        :param width: field width in arcminutes
        :param height: field height in arcminutes

        :return: asset object
        """
        if width == height:
            size = str(width)
        else:
            size = '{},{}'.format(width, height)
        return DataProviderAsset(
            name='{}_{}'.format(survey, position.replace(' ', '_')),
            collection=False,
            path='{}\\{}\\{}'.format(survey, position, size),
            metadata={
                'type': 'FITS', 'survey': survey, 'position': position,
                'fov_ra': width, 'fov_dec': height,
                'layers': 1,
            },
        )

    @staticmethod
    def _get_query_args(survey: str, width: float, height: float) -> dict:
        """
        Return extra astroquery.skyview query arguments for the given field size

        :param survey: survey name
        :param width:  field width in arcminutes
        :param height: field height in arcminutes

        :return: query arguments
        """
        # General query parameters
        kwargs = {
            'survey': survey,
            'cache': False,
            'show_progress': False,
        }

        try:
            scale = survey_scales[survey]
        except KeyError:
            # Unknown scale: query region of the given size, resample to 1K
            from ..imaging_surveys import default_size
            if width > height:
                w, h = int(default_size*width/height + 0.5), default_size
            else:
                w, h = default_size, int(default_size*height/width + 0.5)
            # noinspection PyUnresolvedReferences
            kwargs['sampler'] = 'Spline5'
            # noinspection PyUnresolvedReferences
            kwargs['width'], kwargs['height'] = width*u.arcmin, height*u.arcmin
        else:
            # Assuming default scale for the survey, set the number of pixels
            # from pixel scale
            w, h = int(width*60/scale + 0.5), int(height*60/scale + 0.5)
        kwargs['pixels'] = '{},{}'.format(w, h)
        return kwargs

    # noinspection PyShadowingBuiltins
    def find_assets(self, path: Optional[str] = None, survey: str = 'DSS',
                    ra_hours: Optional[float] = None,
                    dec_degs: Optional[float] = None,
                    object: Optional[str] = None,
                    width: Optional[float] = None,
                    height: Optional[float] = None) \
            -> TList[DataProviderAsset]:
        """
        Return a list of assets matching the given parameters

        Returns an empty list if survey is unknown or no imaging data at the
        given FOV; otherwise, returns a single asset

        :param path: path to the collection asset to search in; ignored
        :param survey: survey name; should be one of those returned by
            the /imaging-surveys resource; default: DSS
        :param ra_hours: RA of image center in hours; used in conjunction
            with `dec_degs` and is mutually exclusive with `object`
        :param dec_degs: Dec of image center in degrees; used in conjunction
            with `ra_hours` and is mutually exclusive with `object`
        :param object: object name resolvable by SIMBAD or NED or coordinates
            like "01 23 45.6, +12 34 56.7"
        :param width: image width in arcminutes
        :param height: image height in arcminutes; default: same as `width`

        :return: list of 0 ro 1 :class:`DataProviderAsset` objects for assets
            matching the query parameters
        """
        if all(item is None for item in (ra_hours, dec_degs, object)):
            raise MissingFieldError('ra_hours,dec_degs|object')
        if (ra_hours is not None or dec_degs is not None) and \
                object is not None:
            raise ValidationError(
                'ra_hours,dec_degs|object',
                '"ra_hours"/"dec_degs" are mutually exclusive with "object"')
        if object is None and (ra_hours is None or dec_degs is None):
            raise MissingFieldError('ra_hours,dec_degs')
        if width is None and height is None:
            raise MissingFieldError('width,height')
        if ra_hours is not None:
            try:
                ra_hours = float(ra_hours)
                if not 0 <= ra_hours < 23:
                    raise ValueError()
            except ValueError:
                raise ValidationError('ra_hours', 'Expected 0 <= ra_hours < 23')
        if dec_degs is not None:
            try:
                dec_degs = float(dec_degs)
                if not -90 <= dec_degs <= 90:
                    raise ValueError()
            except ValueError:
                raise ValidationError(
                    'dec_degs', 'Expected -90 <= dec_degs <= 90')
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

        # noinspection PyProtectedMember
        if survey not in SkyView._valid_surveys:
            # Unknown survey
            return []

        if object is None:
            # Convert FOV center coordinates to standard form
            # noinspection PyUnresolvedReferences
            object = '{}, {}'.format(
                Angle(ra*u.hour).to_string(sep=' ', precision=3, pad=2),
                Angle(dec*u.deg).to_string(sep=' ', precision=2,
                                           alwayssign=True, pad=2))

        # Query SkyView; zero or one result is expected
        # noinspection PyBroadException
        try:
            kwargs = self._get_query_args(survey, width, height)
            kwargs.pop('show_progress')
            res = SkyView.get_image_list(object, **kwargs)
        except Exception:
            return []
        if not res:
            return []
        return [self._get_asset(survey, object, width, height)]

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
        survey, position, width, height = self._get_asset_params(path)
        try:
            res = SkyView.get_images(
                position, **self._get_query_args(survey, width, height))
        except Exception:
            raise AssetNotFoundError(path=path)
        if not res:
            raise AssetNotFoundError(path=path)
        buf = BytesIO()
        res[0].writeto(buf, output_verify='silentfix+ignore')
        return buf.getvalue()
