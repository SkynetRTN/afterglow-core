"""
Afterglow Core: API v1 data provider views
"""

from typing import Optional, Union

from flask import Response, request

from .... import app, errors, json_response
from ....auth import auth_required, current_user
from ....resources.data_providers import providers
from ....resources.data_files import (
    get_data_file, get_data_file_bytes, get_data_file_group,
    get_data_file_group_bytes, update_data_file_asset,
    update_data_file_group_asset)
from ....schemas.api.v1 import DataProviderAssetSchema, DataProviderSchema
from ....errors.auth import NotAuthenticatedError
from ....errors.data_provider import (
    UnknownDataProviderError, ReadOnlyDataProviderError,
    NonBrowseableDataProviderError, NonSearchableDataProviderError,
    CannotSearchInNonCollectionError, CannotDeleteNonEmptyCollectionAssetError,
    UploadNotAllowedError)
from ....errors.data_file import UnknownDataFileGroupError
from . import url_prefix


resource_prefix = url_prefix + 'data-providers/'


@app.route(resource_prefix[:-1])
@app.route(resource_prefix + '<id>')
@auth_required('user')
def data_providers(id: Optional[Union[int, str]] = None) -> Response:
    """
    Return data provider(s)

    GET /data-providers
        - return a list of all registered data providers

    GET /data-providers/[id]
        - return a single data provider with the given ID or name

    :param id: data provider ID (int or str) or name

    :return: JSON response containing the list of serialized data provider
        objects when no ID supplied or a single provider otherwise
    """
    if id is None:
        # List only data providers allowed for the current user's auth method
        allowed_providers = []
        for id in sorted({provider.id for provider in providers.values()}):
            provider = providers[id]
            try:
                provider.check_auth()
            except NotAuthenticatedError:
                pass
            else:
                allowed_providers.append(provider)
        return json_response(
            [DataProviderSchema(provider) for provider in allowed_providers])

    try:
        provider = providers[id]
    except KeyError:
        try:
            provider = providers[int(id)]
        except (KeyError, ValueError):
            raise UnknownDataProviderError(id=id)

    # If specific auth method(s) are requested for data provider, check that the
    # user is authenticated with any of these methods
    provider.check_auth()

    return json_response(DataProviderSchema(provider))


@app.route(resource_prefix + '<id>/assets', methods=('GET', 'PUT', 'DELETE'))
@auth_required('user')
def data_providers_assets(id: Union[int, str]) -> Response:
    """
    Return data provider asset metadata, rename or delete assets

    GET /data-providers/[id]/assets?path=...
        - return a one-element list containing metadata for the asset
          at the given path

    GET /data-providers/[id]/assets?[path=...&]param=value...
        - return metadata for the assets matching the given parameters;
          for data providers that have collection assets, the optional path
          defines a collection asset to search in; data provider must be
          searchable

    PUT /data-providers/[id]/assets?path=...&name=...
        - rename an existing asset at the given path; data provider must
          be writable

    DELETE /data-providers/[id]/assets?path=...[&force]
        - delete the existing asset at the given path; data provider must be
          writable; adding "force" recursively deletes non-empty collection
          assets

    :param id: data provider ID (int or str) or name for which the assets
        are managed

    :return: request-dependent JSON response, see above
    """
    try:
        provider = providers[id]
    except KeyError:
        try:
            provider = providers[int(id)]
        except (KeyError, ValueError):
            raise UnknownDataProviderError(id=id)
    provider.check_auth()

    if request.method != 'GET' and provider.readonly:
        raise ReadOnlyDataProviderError(id=id)

    params = request.args.to_dict()
    path = params.pop('path', None)
    if path is not None:
        path = str(path)

    if request.method == 'GET':
        # Get sorting/pagination parameters
        sort_by = params.pop('sort', None)
        page_size = params.pop('page[size]', None)
        page = params.pop('page[number]', None)
        page_after = params.pop('page[after]', None)
        page_before = params.pop('page[before]', None)

        if params:
            # "Search" request
            if not provider.searchable:
                raise NonSearchableDataProviderError(id=id)

            # If provided, path must identify a collection asset
            if path is not None and not provider.get_asset(path).collection:
                raise CannotSearchInNonCollectionError()

            assets, total_pages, first, last = provider.find_assets(
                path=path, sort_by=sort_by, page_size=page_size, page=page,
                page_after=page_after, page_before=page_before, **params)
            return json_response(
                [DataProviderAssetSchema(asset) for asset in assets],
                include_pagination=True, total_pages=total_pages,
                first=first, last=last)

        # "Get" request; assume empty path by default
        if path is None:
            path = ''
        asset = provider.get_asset(path)
        if asset.collection:
            # "Browse" request
            if not provider.browseable:
                raise NonBrowseableDataProviderError(id=id)
            assets, total_pages, first, last = provider.get_child_assets(
                path, sort_by=sort_by, page_size=page_size, page=page,
                page_after=page_after, page_before=page_before)
            return json_response(
                [DataProviderAssetSchema(asset) for asset in assets],
                include_pagination=True, total_pages=total_pages,
                first=first, last=last)
        return json_response([DataProviderAssetSchema(asset)])

    # POST/PUT/DELETE always work with asset(s) at the given path
    if path is None:
        raise errors.MissingFieldError(field='path')

    if request.method == 'PUT':
        # Rename asset at the given path
        name = params.pop('name', None)
        if not name:
            raise errors.MissingFieldError(field='name')
        return json_response(DataProviderAssetSchema(provider.rename_asset(
            path, name, **params)))

    if request.method == 'DELETE':
        force = params.pop('force', False)
        if force is None:
            force = True
        else:
            force = bool(int(force))

        # Check that the asset at the given path exists
        asset = provider.get_asset(path)

        # "force" is required to recursively delete a non-empty collection asset
        if asset.collection and provider.get_child_assets(path) and not force:
            raise CannotDeleteNonEmptyCollectionAssetError()

        provider.delete_asset(path, **params)
        return json_response()


@app.route(resource_prefix + '<id>/assets/data', methods=('GET', 'POST', 'PUT'))
@auth_required('user')
def data_providers_assets_data(id: Union[int, str]) -> Response:
    """
    Download, create, or update asset data

    For all requests except GET, data provider must be writable.

    GET /data-providers/[id]/assets/data?path=...
        - download unmodified non-collection asset data directly to the caller
          in form data

    POST /data-providers/[id]/assets/data?path=
        - create a new non-collection asset from a data file uploaded
          as multipart/form-data
        - create a new empty collection asset if request body is empty

    POST /data-providers/[id]/assets/data?path=...&data_file_id=...[&fmt=...]
        - create a new non-collection asset at the given path from data file
          using the specified file format (by default, same as the original file
          if the data file was imported or FITS otherwise)

    POST /data-providers/[id]/assets/data?path=...&group_name=...
        [&fmt=...&mode=...]
        - create a new non-collection asset at the given path from data file
          group using the specified file format (by default, same as
          the original file if the data file was imported or FITS otherwise)
          and image mode (by default, L, RGB, or RGBA, depending on the number
          of files in the group; see also
          https://pillow.readthedocs.io/en/stable/handbook/concepts.html)

    POST /data-providers/[id]/assets/data?path=...&src_path=...
        [&src_provider_id=...][&move]
        - copy/move asset to another path within the same data provider or
          (if "src_provider_id" is supplied) from a different data provider
          * if "move" is present, the original asset is deleted

    PUT /data-providers/[id]/assets?path=...[&force]
        - update existing asset data at the given path by overwriting it
          with the data uploaded as multipart/form-data or creating an empty
          collection asset if no data provided
          * existing collection assets are overwritten if "force" is present

    PUT /data-providers/[id]/assets?[path=...&]&data_file_id=...[&fmt=...]
        [&force]
        - update existing asset at the given path by overwriting it with
          the given data file in the original or some other format
          * existing collection assets are overwritten if "force" is present
          * if no path provided, the original asset path of the data file
            previously imported from this data provider is used

    PUT /data-providers/[id]/assets?[path=...&]&group_name=...
        [&fmt=...&mode=...][&force]
        - update existing asset at the given or the original path by overwriting
          it with the given data file group combined into a single file
          in the original or some other format

    PUT /data-providers/[id]/assets/data?path=...&src_path=...
        [&src_provider_id=...][&move][&force]
        - update existing asset by copying from another path within the same
          data provider or (if "src_provider_id" is supplied) from a different
          data provider
          * existing collection assets are overwritten if "force" is present
          * if "move" is present, the original asset is deleted

    :param id: data provider ID (int or str) or name for which the assets
        are managed

    :return: request-dependent JSON response, see above
    """
    try:
        provider = providers[id]
    except KeyError:
        try:
            provider = providers[int(id)]
        except (KeyError, ValueError):
            raise UnknownDataProviderError(id=id)
    provider.check_auth()

    if request.method != 'GET' and provider.readonly:
        raise ReadOnlyDataProviderError(id=id)

    params = request.args.to_dict()
    path = params.pop('path', None)
    if not path:
        if request.method == 'GET' or params.get('src_path') is not None:
            # Path is required for GET and for copy/move operations
            raise errors.MissingFieldError(field='path')

        # When POSTing/PUTting from a data file or a data file group,
        # and the target path is not set, save to the original path
        # if available, same for all files in the group, and is in the same
        # data provider
        if params.get('group_name'):
            group = get_data_file_group(current_user.id, params['group_name'])
            if not group:
                UnknownDataFileGroupError(group_name=params['group_name'])
            if all(getattr(df, 'data_provider', None) == str(id)
                   for df in group) and len(set(
                    df.asset_path for df in group
                    if getattr(df, 'asset_path', None))) == 1:
                path = group[0].asset_path
        elif params.get('data_file_id'):
            df = get_data_file(current_user.id, params['data_file_id'])
            if getattr(df, 'data_provider', None) == str(id):
                path = getattr(df, 'asset_path', None)
        if not path:
            raise errors.MissingFieldError(field='path')
    else:
        path = str(path)

    if request.method == 'GET':
        # Non-collection asset download request
        asset = provider.get_asset(path)
        if asset.collection:
            raise errors.ValidationError(
                'path', 'Cannot download collection assets')
        data = provider.get_asset_data(path)

        return Response(
            data, 200 if data else 204, [('Content-Length', str(len(data)))],
            asset.mimetype)

    if request.method in ('POST', 'PUT'):
        group_name = params.pop('group_name', None)
        data_file_id = params.pop('data_file_id', None)
        src_provider_id = params.pop('src_provider_id', None)
        src_path = params.pop('src_path', None)
        if src_path is None:
            # Saving a data file/group or uploading
            if src_provider_id is not None:
                raise errors.ValidationError(
                    'src_provider_id',
                    '"src_provider_id" is not allowed with "group_name" and '
                    '"data_file_id"')

            fmt = params.pop('fmt', None)
            mode = params.pop('mode', None)

            # Retrieve data being exported
            if group_name is not None:
                # Exporting data file group using the given format and mode
                if data_file_id is not None:
                    raise errors.ValidationError(
                        'data_file_id',
                        '"group_name" and "data_file_id" are mutually '
                        'exclusive')
                data = get_data_file_group_bytes(
                    current_user.id, group_name, fmt=fmt, mode=mode)
            elif data_file_id is not None:
                # Exporting single data file in the given format
                data = get_data_file_bytes(
                    current_user.id, data_file_id, fmt=fmt)
            else:
                # Creating/updating from uploaded data; use the first
                # multipart/form-data file; if empty, creating an empty
                # collection asset
                try:
                    data = list(request.files.values())[0].read()
                except (AttributeError, IndexError):
                    if not provider.allow_upload:
                        raise UploadNotAllowedError()
                    data = None

            provider.check_quota(
                path if request.method == 'PUT' else None, data)

            if request.method == 'POST':
                # Create non-collection asset from data or empty collection
                # asset if no data provided
                asset = provider.create_asset(path, data, **params)
            else:
                # Update asset
                force = params.pop('force', False)
                if force is None:
                    force = True
                else:
                    force = bool(int(force))
                asset = provider.update_asset(path, data, force=force, **params)

            # Link the original data files to the new asset and reset
            # the modified flag on save
            if data_file_id is not None:
                update_data_file_asset(
                    current_user.id, data_file_id, id, asset.path,
                    asset.metadata, asset.name)
            elif group_name is not None:
                update_data_file_group_asset(
                    current_user.id, group_name, id, asset.path,
                    asset.metadata, asset.name)

            return json_response(
                DataProviderAssetSchema(asset),
                201 if request.method == 'POST' else 200)

        # Recursively copying from another asset
        src_path = str(src_path)
        move = params.pop('move', False)
        if move is None:
            move = True
        else:
            move = bool(int(move))
        force = params.pop('force', False)
        if force is None:
            force = True
        else:
            force = bool(int(force))
        if src_provider_id is None or src_provider_id == id:
            src_provider = provider
        else:
            try:
                src_provider = providers[src_provider_id]
            except KeyError:
                try:
                    src_provider = providers[int(src_provider_id)]
                except (KeyError, ValueError):
                    raise UnknownDataProviderError(id=src_provider_id)
            if src_provider != provider:
                src_provider.check_auth()
                if move and src_provider.readonly:
                    raise ReadOnlyDataProviderError(id=src_provider.id)
        if src_provider == provider and src_path == path:
            raise errors.ValidationError(
                'src_path',
                '{}ing onto itself'.format(('Copy', 'Mov')[move]))

        update = request.method == 'PUT'
        return json_response(DataProviderAssetSchema(provider.recursive_copy(
            src_provider, src_path, path, move=move, update=update,
            force=force)), 200 if update else 201)
