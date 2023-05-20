"""
Afterglow Core: OAuth2 provider endpoints
"""

# noinspection PyProtectedMember
from flask import Response, current_app, request, g

from ... import json_response
from ...auth import oauth_plugins, set_access_cookies, user_login
from ...resources import users
from ...errors import MissingFieldError
from ...errors.auth import UnknownAuthMethodError, NotAuthenticatedError
from . import ajax_blp as blp


@blp.route('/oauth2/providers', methods=['GET'])
def oauth2_providers() -> Response:
    """
    Return available OAuth2 plugins

    :return:
        GET /ajax/oauth2/providers: list of OAuth2 plugins
    """
    plugins = [dict(id=p.id, icon=p.icon, description=p.description,
                    authorize_url=p.authorize_url, client_id=p.client_id,
                    request_token_params=p.request_token_params)
               for p in oauth_plugins.values()]

    return json_response(plugins)


@blp.route('/oauth2/providers/<string:plugin_id>/authorized')
def oauth2_authorized(plugin_id: str) -> Response:
    """
    OAuth2.0 authorization code granted redirect endpoint

    :param plugin_id: OAuth2 plugin ID

    :return: redirect to original request URL
    """
    # Do not allow login if Afterglow Core has not yet been configured
    # if DbUser.query.count() == 0:
    #     raise NotInitializedError()

    if not plugin_id or plugin_id not in oauth_plugins.keys():
        raise UnknownAuthMethodError(method=plugin_id)

    oauth_plugin = oauth_plugins[plugin_id]

    if not request.args.get('code'):
        raise MissingFieldError('code')

    if not request.args.get('redirect_uri'):
        raise MissingFieldError('redirect_uri')

    redirect_uri = request.args.get('redirect_uri')

    token = oauth_plugin.get_token(request.args.get('code'), redirect_uri)
    return user_login(oauth_plugin.get_user(token), oauth_plugin)
