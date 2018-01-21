"""
Afterglow Access Server: data-providers resource

The list of data provider plugins loaded at runtime is controlled by the
DATA_PROVIDERS configuration variable.
"""

from __future__ import absolute_import, division, print_function
from flask import request
from .. import app, errors, json_response, plugins, url_prefix
from ..auth import NotAuthenticatedError, auth_plugins, auth_required
from . import data_provider_plugins


__all__ = [
    'providers',
    'UnknownDataProviderError', 'ReadOnlyDataProviderError',
    'NonBrowseableDataProviderError', 'NonSearchableDataProviderError',
    'AssetNotFoundError', 'AssetAlreadyExistsError',
    'CannotSearchInNonCollectionError', 'CannotUpdateCollectionAssetError',
    'CannotDeleteNonEmptyCollectionAssetError', 'QuotaExceededError',
]


class UnknownDataProviderError(errors.AfterglowError):
    """
    The user requested an unknown data provider

    Extra attributes::
        id: data provider ID requested
    """
    code = 404
    subcode = 1000
    message = 'Unknown data provider ID'


class ReadOnlyDataProviderError(errors.AfterglowError):
    """
    The user requested a POST, PUT, or DELETE for an asset of a read-only
    data provider

    Extra attributes::
        id: data provider ID requested
    """
    code = 403
    subcode = 1001
    message = 'Read-only data provider'


class NonBrowseableDataProviderError(errors.AfterglowError):
    """
    The user requested a GET for a collection asset of a non-browseable data
    provider

    Extra attributes::
        id: data provider ID requested
    """
    code = 403
    subcode = 1002
    message = 'Non-browseable data provider'


class NonSearchableDataProviderError(errors.AfterglowError):
    """
    The user requested a GET with search keywords for an asset of
    a non-searchable data provider

    Extra attributes::
        id: data provider ID requested
    """
    code = 403
    subcode = 1003
    message = 'Non-searchable data provider'


class AssetNotFoundError(errors.AfterglowError):
    """
    No asset found at the given path

    Extra attributes::
        path: requested asset path
    """
    code = 404
    subcode = 1004
    message = 'No asset found at the given path'


class AssetAlreadyExistsError(errors.AfterglowError):
    """
    Attempt to create asset over the existing path

    Extra attributes::
        None
    """
    code = 403
    subcode = 1005
    message = 'Asset already exists at the given path'


class CannotSearchInNonCollectionError(errors.AfterglowError):
    """
    Attempt to search within a path that identifies a non-collection resource

    Extra attributes::
        None
    """
    code = 403
    subcode = 1006
    message = 'Can only search in collection assets'


class CannotUpdateCollectionAssetError(errors.AfterglowError):
    """
    Attempt to update a collection asset

    Extra attributes::
        None
    """
    code = 403
    subcode = 1007
    message = 'Cannot update a collection asset'


class CannotDeleteNonEmptyCollectionAssetError(errors.AfterglowError):
    """
    Attempt to delete a non-empty collection asset

    Extra attributes::
        None
    """
    code = 403
    subcode = 1008
    message = 'Cannot delete non-empty collection asset without "force"'


class QuotaExceededError(errors.AfterglowError):
    """
    Attempting to create/update an asset of a read-write data provider would
    exceed the user quota

    Extra attributes::
        quota: storage quota in bytes
        usage: used storage
        size: size of asset being created or updated
    """
    code = 403
    subcode = 1009
    message = 'Storage quota exceeded'


def _check_provider_auth(provider):
    """
    Check that the user is authenticated with any of the auth methods required
    for the given data provider; raises NotAuthenticatedError if not

    :param DataProvider provider: data provider plugin instance

    :return: None
    """
    if not auth_plugins:
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


resource_prefix = url_prefix + 'data-providers/'


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
        # Data provider listing is available to all users authorized for any of
        # the data provider
        auth_methods = []
        for provider in providers.values():
            auth_methods += [
                method for method in provider.auth_methods
                if method not in auth_methods]
        return json_response(
            [provider for id, provider in providers.items()
             if isinstance(id, int)])

    try:
        provider = providers[id]
    except KeyError:
        try:
            provider = providers[int(id)]
        except (KeyError, ValueError):
            raise UnknownDataProviderError(id=id)

    # If specific auth method(s) are requested for data provider, check that the
    # user is authenticated with any of these methods
    _check_provider_auth(provider)

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
    _check_provider_auth(provider)

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
            data = get_data_file_data(data_file_id)
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


# Load data provider plugins
providers = plugins.load_plugins(
    'data provider', 'resources.data_provider_plugins',
    data_provider_plugins.DataProvider, app.config.get('DATA_PROVIDERS', []))
