"""
Afterglow Core: HTTP auth provider endpoints
"""

# noinspection PyProtectedMember
from flask import Response, request

from ... import json_response
from ...auth import http_auth_plugins, user_login
from ...errors import MissingFieldError
from ...errors.auth import UnknownAuthMethodError
from . import ajax_blp as blp


@blp.route('/http_auth/providers', methods=['GET'])
def http_auth_providers() -> Response:
    """
    Return available HTTP auth plugins

    :return:
        GET /ajax/http_auth/providers: list of HTTP auth plugins
    """
    plugins = [dict(id=p.id, icon=p.icon, description=p.description)
               for p in http_auth_plugins.values()]

    return json_response(plugins)


@blp.route('/http_auth/providers/<string:plugin_id>/authorize')
def http_auth_login(plugin_id: str) -> Response:
    """
    HTTP auth login endpoint

    :param plugin_id: HTTP auth plugin ID

    :return: redirect to original request URL
    """
    if not plugin_id or plugin_id not in http_auth_plugins:
        raise UnknownAuthMethodError(method=plugin_id)

    http_auth_plugin = http_auth_plugins[plugin_id]

    if not request.args.get('username'):
        raise MissingFieldError('username')

    if not request.args.get('password'):
        raise MissingFieldError('password')

    return user_login(http_auth_plugin.get_user(
        request.args['username'], request.args['password']), http_auth_plugin)
