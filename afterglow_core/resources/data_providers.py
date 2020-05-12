#TODO remove unused imports
"""
Afterglow Core: data-providers resource

The list of data provider plugins loaded at runtime is controlled by the
DATA_PROVIDERS configuration variable.
"""

from __future__ import absolute_import, division, print_function
from flask import request
from .. import app, errors, json_response, plugins
from ..auth import oauth_plugins, auth_required, current_user
from ..errors.auth import NotAuthenticatedError
from ..errors.data_provider import (
    UnknownDataProviderError, ReadOnlyDataProviderError,
    NonBrowseableDataProviderError, NonSearchableDataProviderError,
    AssetNotFoundError, AssetAlreadyExistsError,
    CannotSearchInNonCollectionError, CannotDeleteNonEmptyCollectionAssetError,
    QuotaExceededError)
from . import data_provider_plugins


__all__ = [
    'providers',
]


def _check_provider_auth(provider):
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



# Load data provider plugins
providers = plugins.load_plugins(
    'data provider', 'resources.data_provider_plugins',
    data_provider_plugins.DataProvider, app.config.get('DATA_PROVIDERS', []))
