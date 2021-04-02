"""
Afterglow Core: settings routes
"""

import secrets
import json

from flask import Response, request, redirect
from marshmallow.fields import Integer, String

from ...auth import oauth_plugins

from ... import app, json_response
from ...auth import auth_required, set_access_cookies
from ...resources.users import DbPersistentToken, db, DbUser, DbIdentity, DbRole
from ...schemas import Resource
from ...errors import ValidationError, MissingFieldError
from ...errors.auth import (
    HttpAuthFailedError, UnknownTokenError, NotInitializedError, UnknownAuthMethodError,
    NotAuthenticatedError, InitPageNotAvailableError)

from . import url_prefix


@app.route(url_prefix + 'oauth2_plugins', methods=['GET'])
def oauth2_plugins() -> Response:
    """
    Return available OAuth2 plugins

    :return:
        GET /ajax/oauth_plugins: list of OAuth2 plugins
    """

    plugins = [dict(id=p.id, icon=p.icon, description=p.description,
                    authorizeUrl=p.authorize_url, client_id=p.client_id, request_token_params=p.request_token_params) for p in oauth_plugins.values()]

    return json_response(plugins)

