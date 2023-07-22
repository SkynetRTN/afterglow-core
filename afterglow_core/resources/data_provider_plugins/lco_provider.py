"""
Afterglow Core: Las Cumbres Observatory data provider

Accessing LCO data requires the user to authenticate via LCO HTTP auth service.
The user's LCO username becomes their Afterglow username.
"""

from typing import Any, Dict as TDict, List as TList, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse
from io import BytesIO
import json

from flask_login import current_user
import requests
import astropy.io.fits as pyfits

from ... import PaginationInfo
from ...models import DataProvider, DataProviderAsset
from ...errors import AfterglowError, ValidationError
from ...errors.data_provider import AssetNotFoundError


__all__ = ['LCODataProvider']


MAX_PAGE_SIZE = 500

# Mapping of LCO to Skynet filter names
LCO_FILTER_MAP = {
    'up': 'uprime', 'gp': 'gprime', 'rp': 'rprime', 'ip': 'iprime',
    'u-SDSS': 'uprime', "u'": 'uprime', 'g-SDSS': 'gprime', 'r-SDSS': 'rprime',
    'i-SDSS': 'iprime', 'z-SDSS': 'zprime',
    'Bessell-V': 'V',
    'H-Alpha': 'Halpha', 'ha': 'Halpha', 'H-Beta': 'Hbeta', 'O-III': 'OIII',
    'None': 'Open', 'none': 'Open', '<NO FILTER>': 'Open', 'NO_FILTER': 'Open',
    'air': 'Open', 'clear': 'Clear', 'Astrodon-Exo': 'Exop',
}

USER_OBS = 'User Observations'
COLLAB_OBS = 'Collaboration Observations'
OBS_CATEGORIES = (USER_OBS, COLLAB_OBS)


class LCONotAuthenticatedError(AfterglowError):
    """
    Not authenticated as an LCO user
    """
    code = 403
    message = 'LCO authentication required'


class LCOError(AfterglowError):
    """
    API returned an error
    """
    code = 400


def get_token() -> str:
    """
    Return authenticated user's LCO API token; raises NotAuthenticatedError
    if no valid LCO auth info was provided by any of the auth plugins

    :return: LCO API token
    """
    # The user must have an LCO identity
    try:
        identity = [
            identity for identity in current_user.identities
            if identity.auth_method == 'lco'][0]
    except (AttributeError, IndexError):
        raise LCONotAuthenticatedError(
            error_msg='LCO authentication required')

    identity_data = identity.data
    if not isinstance(identity_data, dict):
        # Needed in job workers
        identity_data = json.loads(identity_data.replace("'", '"'))
    return identity_data['api_token']


def get_username() -> str:
    """
    Return authenticated user's LCO username; raises NotAuthenticatedError
    if no valid LCO auth info was provided by any of the auth plugins

    :return: LCO username
    """
    # The user must have an LCO identity
    try:
        identity = [
            identity for identity in current_user.identities
            if identity.auth_method == 'lco'][0]
    except (AttributeError, IndexError):
        raise LCONotAuthenticatedError(
            error_msg='LCO authentication required')

    identity_data = identity.data
    if not isinstance(identity_data, dict):
        # Needed in job workers
        identity_data = json.loads(identity_data.replace("'", '"'))
    return identity_data['id']


def api_query(root: str, endpoint: str, params: Optional[TDict] = None) \
        -> TDict:
    """
    Run an LCO API query

    :param root: root API URL
    :param endpoint: API endpoint
    :param params: optional request parameters as a dict

    :return: API response
    """
    res = requests.get(
        f'{root}/{endpoint}/', params=params,
        headers={'Authorization': f'Token {get_token()}'})
    if not res.ok:
        e = AfterglowError(error_msg=res.reason)
        e.message = res.reason
        e.code = res.status_code
        raise e
    try:
        res = res.json()
    except Exception:
        raise LCOError(error_msg=res.text)
    if 'detail' in res:
        raise LCOError(error_msg=res['detail'])
    return res


def observe_api_query(endpoint: str, params: Optional[TDict] = None) -> TDict:
    """
    Run an LCO Observation API query

    :param endpoint: API endpoint
    :param params: optional request parameters as a dict

    :return: API response
    """
    return api_query('https://observe.lco.global/api', endpoint, params)


def archive_api_query(endpoint: str = 'frames',
                      params: Optional[TDict] = None) -> TDict:
    """
    Run an LCO Observation API query

    :param endpoint: API endpoint
    :param params: optional request parameters as a dict

    :return: API response
    """
    return api_query('https://archive-api.lco.global', endpoint, params)


def split_asset_path(path: str, allow_collab_obs: bool) \
        -> Tuple[Optional[str], Optional[str], Optional[str], Optional[int]]:
    """
    Return the four parts of the full asset path
    [proposal]/[category]/[target]/[frame]

    :param path: full or partial asset path
    :param allow_collab_obs: allow collaborators' observations

    :return: a tuple (proposal, category, target, frame)
    """
    if path is not None:
        path = str(path).strip(' /')
    if not path:
        # Root path
        return (None,)*4
    components = [s.strip() for s in path.split('/')]
    if len(components) > 4:
        raise ValidationError(
            'path',
            'Expected asset path in the form [/][proposal][/category][/target]'
            '[/frame id]')
    if not components:
        # Root path
        return (None,)*4

    proposal = components[0]
    components = components[1:]
    category = target = frame = None
    if not components:
        # Proposal only
        return proposal, category, target, frame

    if allow_collab_obs:
        category = components[0]
        components = components[1:]
        if category.lower() not in [cat.lower() for cat in OBS_CATEGORIES]:
            raise ValidationError(
                'path',
                f'Observation category must be either of {", ".join(OBS_CATEGORIES)}; got "{category}"')
        category = ' '.join(s.capitalize() for s in category.split())
        if not components:
            # Proposal/category
            return proposal, category, target, frame
    else:
        category = USER_OBS

    target = components[0]
    components = components[1:]
    if not components:
        # Proposal/category/target
        return proposal, category, target, frame

    frame = components[0]
    try:
        frame = int(frame)
    except (TypeError, ValueError):
        raise ValidationError(
            'path',
            f'Frame ID must be integer; got "{frame}"')

    # All components present
    return proposal, category, target, frame


def get_image_name(p: TDict[str, Any]) -> str:
    """
    Return display name for a non-collection image asset

    :param p: frame params as returned by the GET /frames/[id] query

    :return: human-readable image name
    """
    flt = LCO_FILTER_MAP.get(
        p['primary_optical_element'].strip('*'),
        p['primary_optical_element'].strip('*'))
    return f'{p["target_name"]}_{flt}_{p["exposure_time"]}s_{p["observation_date"].rstrip("Z")}.fits'


def pagination(res: TDict, page_size: Optional[int] = None,
               page: Optional[int] = None) -> PaginationInfo:
    """
    Return pagination info from the result of an LCO API query

    :param res: query result
    :param page_size: optional number of assets per page
    :param page: optional 0-based page number

    :return: Afterglow pagination info structure
    """
    if page_size is None:
        # Page size not provided by Afterglow frontend, retrieve from LCO
        if res.get('next'):
            params = parse_qs(urlparse(res['next']).query)
            if 'limit' in params:
                # noinspection PyTypeChecker
                page_size = int(params['limit'][0])

    if page_size is None:
        # Try the previous page link
        if res.get('previous'):
            params = parse_qs(urlparse(res['previous']).query)
            if 'limit' in params:
                # noinspection PyTypeChecker
                page_size = int(params['limit'][0])

    if not page_size:
        total_pages = None
    elif not res.get('count'):
        total_pages = 0
    else:
        page_size = int(page_size)
        total_pages = (res['count'] - 1)//page_size + 1

    return PaginationInfo(
        page_size=page_size,
        total_pages=total_pages,
        current_page=int(page or 0))


class LCODataProvider(DataProvider):
    """
    LCO data provider plugin class
    """
    name = 'lco'
    display_name = 'Las Cumbres Observatory'
    description = 'Import images from Las Cumbres Observatory Global ' \
        'Telescope. This provider grants you access to your and your ' \
        'collaborators\' LCO observations.'
    columns = []
    browseable = True
    searchable = True
    search_fields = dict(
        name=dict(label='Asset name', type='text'),
        after=dict(label='Taken After', type='datetime'),
        before=dict(label='Taken Before', type='datetime'),
    )
    readonly = True
    quota = usage = None
    auth_methods = ('lco',)

    allow_collab_obs = True
    allow_multiple_instances = False

    def __init__(self, id: Optional[Union[str, int]] = None,
                 display_name: str = 'Las Cumbres Observatory',
                 icon: Optional[str] = 'lco_btn_icon.png',
                 allow_collab_obs: bool = True, **kwargs):
        """
        Create an LCODataProvider instance

        :param id: unique data provider ID; default: assigned automatically
        :param display_name: optional data provider plugin visible in the
            Afterglow UI; default: "Las Cumbres Observatory"
        :param icon: optional UI icon name; default: "lco_btn_icon.png"
        :param allow_collab_obs: allow listing collaborators' observations
        """
        super().__init__(id=id, display_name=display_name, icon=icon, **kwargs)
        self.allow_collab_obs = allow_collab_obs

    def get_asset(self, path: str) -> DataProviderAsset:
        """
        Return an asset at the given path

        :param path: asset path

        :return: asset object
        """
        proposal, category, target, frame = \
            split_asset_path(path, self.allow_collab_obs)

        if proposal is None:
            # Root asset
            return DataProviderAsset(
                name='',
                collection=True,
                path='',
                metadata={},
            )

        norm_path = proposal
        if (category, target, frame) == (None,)*3:
            # First-level collection asset "proposal"
            return DataProviderAsset(
                name=observe_api_query(f'proposals/{proposal}')['title'],
                collection=True,
                path=norm_path,
                metadata={},
            )

        norm_path += '/' + category
        if (target, frame) == (None,)*2:
            # Collection asset "proposal/category
            return DataProviderAsset(
                name=category,
                collection=True,
                path=norm_path,
                metadata={},
            )

        norm_path += '/' + target.lower()
        if frame is None:
            # Collection asset "proposal/category
            return DataProviderAsset(
                name=target,
                collection=True,
                path=norm_path,
                metadata={},
            )

        # Non-collection frame asset
        norm_path += '/' + str(frame)
        params = archive_api_query(f'frames/{frame}')
        return DataProviderAsset(
            name=get_image_name(params),
            collection=False,
            path=norm_path,
            metadata=dict(
                id=frame,
                type='FITS',
                time=params['observation_date'].rstrip('Z'),
                layers=1,
                telescope=f'{params["site_id"]} - {params["telescope_id"]} - '
                f'{params["instrument_id"]}',
                obs_id=params['observation_id'],
                filter=LCO_FILTER_MAP.get(
                    params['primary_optical_element'].strip('*'),
                    params['primary_optical_element'].strip('*')),
                exposure=params['exposure_time'],
            ),
        )

    def find_assets(self, path: Optional[str] = None,
                    sort_by: Optional[str] = None,
                    page_size: Optional[int] = None,
                    page: Optional[int] = None,
                    name: Optional[str] = None,
                    after: Optional[str] = None,
                    before: Optional[str] = None) \
            -> Tuple[TList[DataProviderAsset], Optional[PaginationInfo]]:
        """
        Return child assets of a collection asset at the given path, optionally
        matching search criteria

        :param path: asset path; must identify a collection asset
        :param sort_by: optional sorting key
        :param page_size: optional number of assets per page
        :param page: optional 0-based page number
        :param name: get assets with names containing the given substring
        :param after: request exposures taken after the given date/time
            (YYYY-MM-DDTHH:MM:SS[.S])
        :param before: request exposures taken before the given date/time
            (YYYY-MM-DDTHH:MM:SS[.S])

        :return: list of :class:`DataProviderAsset` objects for child assets,
            optional total number of pages, and key values for the first and
            last assets on the current page
        """
        proposal, category, target, frame = \
            split_asset_path(path, self.allow_collab_obs)
        if frame is not None:
            # Path to non-collection asset
            raise AssetNotFoundError(path=path)

        # Init pagination
        request_params = {}
        if page_size is not None:
            request_params['limit'] = page_size
            if page is not None:
                if page == 'first':
                    page = 0
                elif page == 'last':
                    page = -1
                request_params['offset'] = page_size*page

        if proposal is None:
            # List all proposals
            if name is not None:
                request_params['title'] = name
            res = observe_api_query('proposals', request_params)
            proposals = res['results']
            return (
                [DataProviderAsset(
                     name=params['title'],
                     collection=True,
                     path=params['id'],
                     metadata={},
                 ) for params in proposals],
                pagination(res, page_size, page))

        norm_path = proposal
        if self.allow_collab_obs:
            if category is None:
                # List all categories
                return (
                    [DataProviderAsset(
                        name=s,
                        collection=True,
                        path=norm_path + '/' + s,
                        metadata={},
                    ) for s in OBS_CATEGORIES], None)

        norm_path += '/' + category
        if target is None:
            # List all targets within the given proposal
            rg_params = {'proposal': proposal}
            if category == USER_OBS:
                rg_params['user'] = get_username()
            res = observe_api_query('requestgroups', rg_params)
            n_request_groups = res['count']
            if len(res['results']) < n_request_groups:
                rg_params['limit'] = n_request_groups
                res = observe_api_query('requestgroups', rg_params)
            request_groups = res['results']
            all_targets = set()
            for rg in request_groups:
                for r in rg['requests']:
                    for c in r['configurations']:
                        all_targets.add(c['target']['name'])
            if name is None:
                all_targets = list(all_targets)
            else:
                name = name.lower()
                all_targets = [target for target in all_targets
                               if name in target.lower()]
            if sort_by:
                if sort_by.lstrip('+-').lower() == 'name':
                    all_targets.sort(
                        key=lambda item: item.lower(),
                        reverse=sort_by.startswith('-'))
            return (
                [DataProviderAsset(
                    name=target_name,
                    collection=True,
                    path=norm_path + '/' + target_name.lower(),
                    metadata={},
                ) for target_name in all_targets],
                PaginationInfo(
                    sort=sort_by, page_size=int(page_size or 100),
                    total_pages=len(all_targets)//int(page_size or 100),
                    current_page=page))

        # Return all frames for the given target
        norm_path += '/' + target.lower()
        request_params['proposal_id'] = proposal
        request_params['target_name'] = target
        if name is not None:
            request_params['basename'] = name
        if after is not None:
            request_params['start'] = after
        if before is not None:
            request_params['end'] = before
        request_params['reduction_level'] = 91  # only return reduced images
        if category == COLLAB_OBS:
            # Return all frames for the given target name
            res = archive_api_query('frames', request_params)
            return (
                [DataProviderAsset(
                     name=get_image_name(params),
                     collection=False,
                     path=norm_path + '/' + str(params['id']),
                     metadata=dict(
                         id=params['id'],
                         type='FITS',
                         time=params['observation_date'].rstrip('Z'),
                         layers=1,
                         telescope=f'{params["site_id"]} - '
                         f'{params["telescope_id"]} - '
                         f'{params["instrument_id"]}',
                         obs_id=params['observation_id'],
                         filter=LCO_FILTER_MAP.get(
                             params['primary_optical_element'].strip('*'),
                             params['primary_optical_element'].strip('*')),
                         exposure=params['exposure_time'],
                     ),
                 ) for params in res['results']],
                pagination(res, page_size, page))

        # For user's observations, get all request groups, then all
        # requests for this target, then all frames for these requests
        target = target.lower()
        username = get_username()
        res = observe_api_query('requestgroups', {'user': username})
        n_request_groups = res['count']
        if len(res['results']) < n_request_groups:
            res = observe_api_query(
                'requestgroups', {'user': username, 'limit': n_request_groups})
        request_groups = res['results']
        all_requests = []
        for rg in request_groups:
            for r in rg['requests']:
                for c in r['configurations']:
                    if target in c['target']['name'].lower():
                        all_requests.append(r['id'])
                        break
        frames = []
        for request in all_requests:
            request_params['request_id'] = request
            res = archive_api_query('frames', request_params)
            n_frames = res['count']
            if len(res['results']) < n_frames:
                request_params['limit'] = n_frames
                res = archive_api_query('frames', request_params)
            frames += [DataProviderAsset(
                name=get_image_name(params),
                collection=False,
                path=norm_path + '/' + str(params['id']),
                metadata=dict(
                    id=params['id'],
                    type='FITS',
                    time=params['observation_date'].rstrip('Z'),
                    layers=1,
                    telescope=f'{params["site_id"]} - '
                              f'{params["telescope_id"]} - '
                              f'{params["instrument_id"]}',
                    obs_id=params['observation_id'],
                    filter=LCO_FILTER_MAP.get(
                        params['primary_optical_element'].strip('*'),
                        params['primary_optical_element'].strip('*')),
                    exposure=params['exposure_time'],
                ),
                ) for params in res['results']
            ]
        if name is not None:
            name = name.lower()
            frames = [frame for frame in frames if name in frame.name.lower()]
        if sort_by:
            if sort_by.lstrip('+-').lower() == 'name':
                frames.sort(
                    key=lambda item: item.name,
                    reverse=sort_by.startswith('-'))
        return frames, PaginationInfo(
            sort=sort_by, page_size=int(page_size or 100),
            total_pages=len(frames)//int(page_size or 100),
            current_page=page)

    def get_child_assets(self, path: str,
                         sort_by: Optional[str] = None,
                         page_size: Optional[int] = None,
                         page: Optional[Union[int, str]] = None) \
            -> Tuple[TList[DataProviderAsset], Optional[PaginationInfo]]:
        """
        Return child assets of a collection asset at the given path

        :param path: asset path; must identify a collection asset
        :param sort_by: optional sorting key
        :param page_size: optional number of assets per page
        :param page: optional 0-based page number, "first", "last", ">value",
            or "<value"

        :return: list of :class:`DataProviderAsset` objects for child assets,
            optional total number of pages, and key values for the first and
            last assets on the current page
        """
        return self.find_assets(
            path=path, sort_by=sort_by, page_size=page_size, page=page)

    def get_asset_data(self, path: str) -> bytes:
        """
        Return data for a non-collection asset at the given path

        :param path: asset path containing frame ID

        :return: asset data
        """
        frame = split_asset_path(path, self.allow_collab_obs)[-1]
        if frame is None:
            raise ValidationError('path', 'Missing frame ID')

        # Obtain frame download URL and retrieve frame data
        buf = BytesIO(requests.get(
            archive_api_query(f'frames/{frame}')['url']).content)

        # Modify header to match Afterglow/Skynet standard
        with pyfits.open(buf, 'update') as f:
            for hdu in f:
                hdr = hdu.header
                if 'FILTER' in hdr:
                    hdr['FILTER'] = LCO_FILTER_MAP.get(
                        hdr['FILTER'].strip('*'), hdr['FILTER'].strip('*'))
            if len(f) == 5:
                # Keep only the primary HDU for reduced images
                for _ in range(3):
                    del f[-1]
            f.flush()
            return buf.getvalue()
