"""
Afterglow Core: OAuth2 server routes
"""
import json

from werkzeug.urls import url_encode
from flask import redirect, request, url_for, render_template, Response, escape
from ... import app
from ...errors import MissingFieldError
from ...errors.oauth2 import UnknownClientError
from ...auth import auth_required, oauth_plugins, set_access_cookies
from ...oauth2 import oauth_clients, oauth_server
from ...resources.users import DbUserClient, DbUser, DbIdentity, db, DbRole
from ...errors.auth import (
    HttpAuthFailedError, UnknownTokenError, NotInitializedError, UnknownAuthMethodError,
    NotAuthenticatedError, InitPageNotAvailableError)
from ...errors import ValidationError, MissingFieldError


@app.route('/oauth2/authorize', methods=['GET'])
@auth_required(allow_redirect=True)
def oauth2_authorize():
    client_id = request.args.get('client_id')
    if not client_id:
        raise MissingFieldError('client_id')

    # Check that the user allowed the client
    if not DbUserClient.query.filter_by(
            user_id=request.user.id, client_id=client_id).count():
        # Redirect users to consent page if the client was not confirmed yet
        dashboard_prefix = app.config.get("DASHBOARD_PREFIX")
        args = url_encode(dict(client_id=client_id, next=request.url))
        return redirect('{dashboard_prefix}/oauth2/consent?{args}'.format(dashboard_prefix=dashboard_prefix, args=args))
        
    return oauth_server.create_authorization_response(grant_user=request.user)


@app.route('/oauth2/token', methods=['POST'])
def oauth2_token():
    return oauth_server.create_token_response()