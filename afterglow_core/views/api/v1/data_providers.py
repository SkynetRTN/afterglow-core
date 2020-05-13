"""
Afterglow Core: API v1 data provider views
"""

from flask import request

from .... import app, errors, json_response, oauth_plugins
from ....auth import auth_required, current_user
from ....resources.data_providers import providers
from ....errors.auth import NotAuthenticatedError
from ....errors.data_provider import (
    UnknownDataProviderError, ReadOnlyDataProviderError,
    NonBrowseableDataProviderError, NonSearchableDataProviderError,
    AssetNotFoundError, AssetAlreadyExistsError,
    CannotSearchInNonCollectionError, CannotDeleteNonEmptyCollectionAssetError,
    QuotaExceededError)
from . import url_prefix


resource_prefix = url_prefix + 'data-providers/'


def check_provider_auth(provider):
    """
    Check that the user is authenticated with any of the auth methods required
    for the given data provider; raises NotAuthenticatedError if not

    :param DataProvider provider: data provider plugin instance

    :return: None
    """
    if not oauth_plugins:
        # User auth disabled, always succeed
        return

    auth_methods = provider.auth_methods
    if not auth_methods:
        auth_methods = app.config.get('DEFAULT_DATA_PROVIDER_AUTH')
    if not auth_methods:
        # No specific auth methods requested
        return

    # Retrieve the currently authenticated user's auth method from access token
    # noinspection PyProtectedMember
    from flask import _request_ctx_stack
    try:
        method = _request_ctx_stack.top.auth_method
    except Exception:
        raise NotAuthenticatedError(
            error_msg='Refresh token does not contain auth method')
    if method not in auth_methods:
        raise NotAuthenticatedError(
            error_msg='Data provider "{}" requires authentication with '
            'methods: {}'.format(provider.id, ', '.join(auth_methods)))


@app.route(resource_prefix[:-1])
@app.route(resource_prefix + '<id>')
@auth_required('user')
def data_providers(id=None):
    """
    Return data provider(s)

    GET /data-providers
        - return a list of all registered data providers

    GET /data-providers/[id]
        - return a single data provider with the given ID or name

    :param int | str id: data provider ID (int or str) or name

    :return: JSON response containing the list of serialized data provider
        objects when no ID supplied or a single provider otherwise
    :rtype: flask.Response
    """
    if id is None:
        # List only data providers allowed for the current user's auth method
        allowed_providers = []
        for id in sorted({provider.id for provider in providers.values()}):
            provider = providers[id]
            try:
                check_provider_auth(provider)
            except NotAuthenticatedError:
                pass
            else:
                allowed_providers.append(provider)
        return json_response(allowed_providers)

    try:
        provider = providers[id]
    except KeyError:
        try:
            provider = providers[int(id)]
        except (KeyError, ValueError):
            raise UnknownDataProviderError(id=id)

    # If specific auth method(s) are requested for data provider, check that the
    # user is authenticated with any of these methods
    check_provider_auth(provider)

    return json_response(provider)


@app.route(resource_prefix + '<id>/assets',
           methods=('GET', 'POST', 'PUT', 'DELETE'))
@auth_required('user')
def data_providers_assets(id):
    """
    Return, create, update, or delete data provider assets

    GET /data-providers/[id]/assets?path=...
        - return a one-element list containing asset at the given path

    GET /data-providers/[id]/assets?[path=...&]param=value...
        - return a list of data provider assets matching the given parameters;
          for data providers that have collection assets, the optional path
          defines a collection asset to search in; data provider must be
          searchable

    POST /data-providers/[id]/assets?path=...[&data_file_id=...]
        - create a new non-collection asset at the given path from data file or
          a collection asset if data_file_id is omitted; data provider must be
          writeable

    PUT /data-providers/[id]/assets?path=...&data_file_id=...
        - update an existing non-collection asset at the given path by
          overwriting it with the given data file; data provider must be
          writeable

    DELETE /data-providers/[id]/assets?path=...[&force]
        - delete the existing asset at the given path; data provider must be
          writeable; adding "force" recursively deletes non-empty collection
          assets

    :param int | str id: data provider ID (int or str) or name for which the
        assets are managed

    :return: request-dependent JSON response, see above
    :rtype: flask.Response
    """
    try:
        provider = providers[id]
    except KeyError:
        try:
            provider = providers[int(id)]
        except (KeyError, ValueError):
            raise UnknownDataProviderError(id=id)
    check_provider_auth(provider)

    if request.method != 'GET' and provider.readonly:
        raise ReadOnlyDataProviderError(id=id)

    params = request.args.to_dict()
    path = params.pop('path', None)

    if request.method == 'GET':
        if params:
            # "Search" request
            if not provider.searchable:
                raise NonSearchableDataProviderError(id=id)

            # If provided, path must identify a collection asset
            if path is not None and not provider.get_asset(path).collection:
                raise CannotSearchInNonCollectionError()

            return json_response(provider.find_assets(path=path, **params))

        # "Get" request; assume empty path by default
        if path is None:
            path = ''
        asset = provider.get_asset(path)
        if asset.collection:
            # "Browse" request
            if not provider.browseable:
                raise NonBrowseableDataProviderError(id=id)
            return json_response(provider.get_child_assets(path))
        return json_response([asset])

    # POST/PUT/DELETE always work with asset(s) at the given path
    if path is None:
        raise errors.MissingFieldError(field='path')

    # Get data file; optional for POST
    data = None
    if request.method in ('POST', 'PUT'):
        data_file_id = params.pop('data_file_id', None)
        if data_file_id is not None:
            from .data_files import get_data_file_data
            data = get_data_file_data(current_user.id, data_file_id)
        elif request.method == 'PUT':
            raise errors.MissingFieldError(field='data_file_id')

        # Check quota
        quota = provider.quota
        if quota:
            usage, size = provider.usage, len(data) if data is not None else 0
            if usage is None:
                usage = 0
            if usage + size > quota:
                raise QuotaExceededError(quota=quota, usage=usage, size=size)

    # Create/update/delete an asset at the given path
    if request.method == 'POST':
        # Check that no asset at the given path exists already
        try:
            provider.get_asset(path)
        except AssetNotFoundError:
            pass
        else:
            raise AssetAlreadyExistsError()

        return json_response(provider.create_asset(path, data, **params), 201)

    if request.method == 'PUT':
        # Check that the asset at the given path exists and is not a collection
        return json_response(provider.update_asset(path, data, **params))

    if request.method == 'DELETE':
        force = 'force' in params
        if force:
            params.pop('force')

        # Check that the asset at the given path exists
        asset = provider.get_asset(path)

        # "force" is required to recursively delete a non-empty collection asset
        if asset.collection and provider.get_child_assets(path) and not force:
            raise CannotDeleteNonEmptyCollectionAssetError()

        provider.delete_asset(path, **params)
        return json_response()
