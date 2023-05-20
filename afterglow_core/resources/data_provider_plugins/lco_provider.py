"""
Afterglow Core: Las Cumbres Observatory data provider

Accessing LCO data requires the user to authenticate via LCO HTTP auth service.
The user's LCO username becomes their Afterglow username.

Asset paths have the following structure: proposal/request group
"""

from typing import Dict as TDict, List as TList, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse
import json

from flask_login import current_user
import requests

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

RAW_IMAGES = 'raw'
REDUCED_IMAGES = 'reduced'
MASTER_CALS = 'master_cals'
IMAGE_TYPES = (RAW_IMAGES, REDUCED_IMAGES, MASTER_CALS)
IMAGE_TYPE_NAME = {
    RAW_IMAGES: 'Raw Images',
    REDUCED_IMAGES: 'Reduced Images',
    MASTER_CALS: 'Master Calibration Images',
}


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
    return identity_data['username']


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
        e = AfterglowError()
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


def split_asset_path(path: str) \
        -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str],
                 Optional[int]]:
    """
    Return the five parts of the full asset path
    [proposal]/[request group]/[request]/[type]/[frame]

    :param path: full or partial asset path

    :return: a tuple (proposal, category, user, request group, request, type,
        frame)
    """
    if path is not None:
        path = str(path).strip(' /')
    if not path:
        # Root path
        return (None,)*5
    components = [s.strip() for s in path.split('/')]
    if len(components) > 5:
        raise ValidationError(
            'path',
            'Expected asset path in the form [/][proposal][/request group id]'
            '[/request id][/frame type][/frame id]')
    if not components:
        # Root path
        return (None,)*5

    proposal = components[0]
    components = components[1:]
    request_group = request = frame_type = frame = None
    if not components:
        # Proposal only
        return proposal, request_group, request, frame_type, frame

    request_group = components[0]
    components = components[1:]
    try:
        request_group = int(request_group)
    except (TypeError, ValueError):
        raise ValidationError(
            'path',
            f'Request group ID must be integer; got "{request_group}"')
    if not components:
        # Proposal/request_group
        return proposal, request_group, request, frame_type, frame

    request = components[0]
    components = components[1:]
    try:
        request = int(request)
    except (TypeError, ValueError):
        raise ValidationError(
            'path',
            f'Request ID must be integer; got "{request}"')
    if not components:
        # Proposal/request_group/request
        return proposal, request_group, request, frame_type, frame

    frame_type = components[0]
    components = components[1:]
    if not frame_type.lower() in IMAGE_TYPES:
        raise ValidationError(
            'path',
            f'Frame type must be either of {", ".join(IMAGE_TYPES)}; got '
            f'"{frame_type}"')
    if not components:
        # Proposal/request_group/request/type
        return proposal, request_group, request, frame_type, frame

    frame = components[0]
    try:
        frame = int(frame)
    except (TypeError, ValueError):
        raise ValidationError(
            'path',
            f'Frame ID must be integer; got "{frame}"')

    # All components present
    return proposal, request_group, request, frame_type, frame


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
    description = 'Las Cumbres Observatory'
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

    allow_multiple_instances = False

    def __init__(self, id: Optional[Union[str, int]] = None,
                 display_name: str = 'Las Cumbres Observatory',
                 icon: Optional[str] = 'lco_btn_icon.png', **kwargs):
        """
        Create an LCODataProvider instance

        :param id: unique data provider ID; default: assigned automatically
        :param display_name: optional data provider plugin visible in the
            Afterglow UI; default: "Las Cumbres Observatory"
        :param icon: optional UI icon name; default: "lco_btn_icon.png"
        """
        super().__init__(id=id, display_name=display_name, icon=icon, **kwargs)

    def get_asset(self, path: str) -> DataProviderAsset:
        """
        Return an asset at the given path

        :param path: asset path

        :return: asset object
        """
        proposal, request_group, request, frame_type, frame = \
            split_asset_path(path)

        if proposal is None:
            # Root asset
            return DataProviderAsset(
                name='',
                collection=True,
                path='',
                metadata={},
            )

        norm_path = proposal
        if (request_group, request, frame_type, frame) == (None,)*4:
            # First-level collection asset "proposal"
            return DataProviderAsset(
                name=observe_api_query(f'proposals/{proposal}')['title'],
                collection=True,
                path=norm_path,
                metadata={},
            )

        norm_path += '/' + str(request_group)
        if (request, frame_type, frame) == (None,)*3:
            # Collection asset "proposal/request_group"
            return DataProviderAsset(
                name=observe_api_query(
                    f'requestgroups/{request_group}')['name'],
                collection=True,
                path=norm_path,
                metadata={},
            )

        norm_path += '/' + str(request)
        if (frame_type, frame) == (None,)*2:
            # Collection asset "proposal/request_group/request"
            params = observe_api_query(f'requests/{request}')
            return DataProviderAsset(
                name=f'{params["id"]} - {", ".join([conf["target"]["name"] for conf in params["configurations"]])}',
                collection=True,
                path=norm_path,
                metadata={},
            )

        norm_path += '/' + frame_type
        if frame is None:
            # Collection asset "proposal/request_group/request/frame_type"
            return DataProviderAsset(
                name=IMAGE_TYPE_NAME[frame_type],
                collection=True,
                path=norm_path,
                metadata={},
            )

        # Non-collection frame asset
        norm_path += '/' + str(frame)
        params = archive_api_query(f'frames/{frame}')
        return DataProviderAsset(
            name=params['basename'],
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
        proposal, request_group, request, frame_type, frame = \
            split_asset_path(path)
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
        if request_group is None:
            # Return all request groups
            request_params['user'] = get_username()
            if name is not None:
                request_params['name'] = name
            res = observe_api_query('requestgroups', request_params)
            request_groups = res['results']
            return (
                [DataProviderAsset(
                     name=params['name'],
                     collection=True,
                     path=norm_path + '/' + str(params['id']),
                     metadata={},
                 ) for params in request_groups],
                pagination(res, page_size, page))

        norm_path += '/' + str(request_group)
        if request is None:
            # Return all requests for the given request group
            group_params = observe_api_query(f'requestgroups/{request_group}')
            group_requests = group_params['requests']
            if name is not None:
                name = name.lower()
                group_requests = [params for params in group_requests
                                  if name in str(params['id'])]
            if page_size:
                page_size = int(page_size)
                offset = int(page or 0)*page_size
                count = len(group_requests)
                group_requests = group_requests[offset:offset+page_size]
                total_pages = count//page_size
            else:
                total_pages = None
            return (
                [DataProviderAsset(
                     name=f'{params["id"]} - '
                     f'{", ".join([conf["target"]["name"] for conf in params["configurations"]])}',
                     collection=True,
                     path=norm_path + '/' + str(params['id']),
                     metadata={},
                 ) for params in group_requests],
                PaginationInfo(
                    page_size=page_size,
                    total_pages=total_pages,
                    current_page=page))

        norm_path += '/' + str(request)
        if frame_type is None:
            # Return all image types for request
            return [DataProviderAsset(
                        name=IMAGE_TYPE_NAME[frame_type],
                        collection=True,
                        path=norm_path + '/' + frame_type,
                        metadata={},
                    ) for frame_type in IMAGE_TYPES], None

        # Return all frames for the given request and image type
        norm_path += '/' + frame_type
        request_params['request_id'] = request
        if name is not None:
            request_params['basename'] = name
        if after is not None:
            request_params['start'] = after
        if before is not None:
            request_params['end'] = before
        if frame_type == MASTER_CALS:
            # Retrieve IDs of all related frames excluding those directly
            # belonging to the request (i.e. raw images)
            res = archive_api_query('frames', request_params)
            all_frames = res['results']
            all_frame_ids = [frame['id'] for frame in all_frames]
            cal_frame_ids = set()
            for frame in all_frames:
                if frame['reduction_level'] != 91:
                    continue
                cal_frame_ids.update([i for i in frame['related_frames']
                                      if i not in all_frame_ids])
            all_frames = [archive_api_query(f'frames/{i}')
                          for i in cal_frame_ids]
        else:
            # Retrieve all frames belonging to the request having
            # the corresponding reduction level
            request_params['reduction_level'] = 0 if frame_type == RAW_IMAGES \
                else 91
            res = archive_api_query('frames', request_params)
            all_frames = res['results']
        return (
            [DataProviderAsset(
                 name=params['basename'],
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
             ) for params in all_frames],
            pagination(res, page_size, page))

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
        frame = split_asset_path(path)[-1]
        if frame is None:
            raise ValidationError('path', 'Missing frame ID')
        return requests.get(
            archive_api_query(f'frames/{frame}')['url']).content
