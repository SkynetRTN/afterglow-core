"""
Afterglow Access Server: imaging survey data provider plugin
"""

from __future__ import absolute_import, division, print_function

from io import BytesIO

from astropy import units as u
from astropy.coordinates import Angle
from astroquery.skyview import SkyView

from . import DataProvider, DataProviderAsset
from ..data_providers import AssetNotFoundError
from ... import errors
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
    # noinspection PyProtectedMember
    search_fields = dict(
        survey=dict(label='Survey', type='multi_choice',
                    enum=SkyView._valid_surveys),
        ra_hours=dict(label='Center RA', type='float', min_val=0, max_val=24),
        dec_degs=dict(label='Center Dec', type='float',
                      min_val=-90, max_val=90),
        object=dict(label='Object', type='text'),
        width=dict(label='Field Width [arcmin]', type='float', min_val=0),
        height=dict(label='Field Height [arcmin]', type='int', min_val=0),
    )
    readonly = True
    quota = usage = None

    @staticmethod
    def _get_asset_params(path):
        r"""
        Decompose asset path into SkyView-specific parameters: survey name,
        position/coordinates, and field width/height in arcminutes

        :param str path: asset path in the form
            <survey>\<position>\<width>,<height>

        :return: tuple (survey, position, width, height)
        :rtype: tuple[str, str, float, float]
        """
        try:
            survey, position, size = path.split('\\')
            width, height = size.split(',')
            width, height = float(width), float(height)
        except (TypeError, ValueError):
            raise AssetNotFoundError(path=path)
        return survey, position, width, height

    @staticmethod
    def _get_asset(survey, position, width, height):
        """
        Return image survey data provider asset for the given parameters

        :param str survey: survey name
        :param str position: field center coordinates or object name
        :param float width: field width in arcminutes
        :param float height: field height in arcminutes

        :return: asset object
        :rtype: DataProviderAsset
        """
        return DataProviderAsset(
            name='{}_{}'.format(survey, position.replace(' ', '_')),
            collection=False,
            path='{}\\{}\\{},{}'.format(survey, position, width, height),
            metadata={
                'type': 'FITS', 'survey': survey, 'position': position,
                'fov_ra': width, 'fov_dec': height,
                'layers': 1,
            },
        )

    @staticmethod
    def _get_query_args(survey, width, height):
        """
        Return extra astroquery.skyview query arguments for the given field size

        :param str survey: survey name
        :param float width:  field width in arcminutes
        :param float height: field height in arcminutes

        :return: query arguments
        :rtype: dict
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
    def find_assets(self, survey='DSS', ra_hours=None, dec_degs=None,
                    object=None, width=None, height=None):
        """
        Return a list of assets matching the given parameters

        Returns an empty list if survey is unknown or no imaging data at the
        given FOV; otherwise, returns a single asset

        :param str survey: survey name; should be one of those returned by
            the /imaging-surveys resource; default: DSS
        :param float ra_hours: RA of image center in hours; used in conjunction
            with `dec_degs` and is mutually exclusive with `object`
        :param float dec_degs: Dec of image center in degrees; used in
            conjunction with `ra_hours` and is mutually exclusive with `object`
        :param str object: object name resolvable by SIMBAD or NED or
            coordinates like "01 23 45.6, +12 34 56.7"
        :param float width: image width in arcminutes
        :param float height: image height in arcminutes; default: same as
            `width`

        :return: list of 0 ro 1 :class:`DataProviderAsset` objects for assets
            matching the query parameters
        :rtype: list[DataProviderAsset]
        """
        if all(item is None for item in (ra_hours, dec_degs, object)):
            raise errors.MissingFieldError('ra_hours,dec_degs|object')
        if (ra_hours is not None or dec_degs is not None) and \
                object is not None:
            raise errors.ValidationError(
                'ra_hours,dec_degs|object',
                '"ra_hours"/"dec_degs" are mutually exclusive with "object"')
        if object is None and (ra_hours is None or dec_degs is None):
            raise errors.MissingFieldError('ra_hours,dec_degs')
        if width is None:
            raise errors.MissingFieldError('width')
        if height is None:
            raise errors.MissingFieldError('height')
        if ra_hours is not None:
            try:
                ra_hours = float(ra_hours)
                if not 0 <= ra_hours < 23:
                    raise ValueError()
            except ValueError:
                raise errors.ValidationError(
                    'ra_hours', 'Expected 0 <= ra_hours < 23')
        if dec_degs is not None:
            try:
                dec_degs = float(dec_degs)
                if not -90 <= dec_degs <= 90:
                    raise ValueError()
            except ValueError:
                raise errors.ValidationError(
                    'dec_degs', 'Expected -90 <= dec_degs <= 90')
        try:
            width = float(width)
            if width <= 0:
                raise ValueError()
        except ValueError:
            raise errors.ValidationError('width', 'Positive FOV width expected')
        try:
            height = float(height)
            if height <= 0:
                raise ValueError()
        except ValueError:
            raise errors.ValidationError(
                'height', 'Positive FOV height expected')

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
            res = SkyView.get_image_list(
                object, **self._get_query_args(survey, width, height))
        except Exception:
            return []
        if not res:
            return []
        return [self._get_asset(survey, object, width, height)]

    def get_asset(self, path):
        r"""
        Return an asset at the given path

        :param str path: asset path in the form
            <survey>\<position>\<width>,<height>

        :return: asset object
        :rtype: DataProviderAsset
        """
        return self._get_asset(*self._get_asset_params(path))

    def get_asset_data(self, path):
        """
        Return data for a non-collection asset at the given path

        :param str path: asset path; must identify a non-collection asset

        :return: asset data
        :rtype: str
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
        res[0].writeto(buf)
        return buf.getvalue()
