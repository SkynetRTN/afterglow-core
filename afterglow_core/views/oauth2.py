"""
Afterglow Core: OAuth2 server routes
"""

from __future__ import absolute_import, division, print_function

import json

from flask import redirect, request, url_for, render_template
from .. import app, json_response
from ..users import Role, User, db
from ..errors import MissingFieldError, ValidationError
from ..errors.auth import (
    NotAuthenticatedError, NotInitializedError, UnknownAuthMethodError)
from ..errors.oauth2 import UnknownClientError
from ..auth import (
    auth_required, create_token, oauth_plugins, set_access_cookies)
from ..oauth2 import oauth_clients, oauth_server
from ..users import UserClient


@app.route('/oauth2/authorize')
@auth_required('user', allow_redirect=True)
def oauth2_authorize():
    client_id = request.args.get('client_id')
    if not client_id:
        raise MissingFieldError('client_id')

    # Check that the user allowed the client
    if not UserClient.query.filter_by(
            user_id=request.user.id, client_id=client_id).count():
        # Redirect users to consent page if the client was not confirmed yet
        return redirect(url_for(
            'oauth2_consent', client_id=client_id, next=request.url))

    return oauth_server.create_authorization_response(grant_user=request.user)


@app.route('/oauth2/token', methods=['POST'])
def oauth2_token():
    return oauth_server.create_token_response()


@app.route('/oauth2/<string:plugin_id>')
def oauth2_authorized(plugin_id):
    """
    OAuth2.0 authorization code granted redirect endpoint

    :return: redirect to original request URL
    :rtype: flask.Response
    """
    # Do not allow login if Afterglow Core has not yet been configured
    if User.query.count() == 0:
        raise NotInitializedError()

    state = request.args.get('state')
    if not state:
        # TODO: render error page
        raise MissingFieldError('state')

    try:
        state = json.loads(state)
    except json.JSONDecodeError:
        # TODO:  render error page
        raise ValidationError('state')

    if not plugin_id or plugin_id not in oauth_plugins.keys():
        # TODO: render error page
        raise UnknownAuthMethodError(method=plugin_id)

    oauth_plugin = oauth_plugins[plugin_id]

    if not request.args.get('code'):
        # TODO: render error page
        raise MissingFieldError('code')

    token = oauth_plugin.get_token(request.args.get('code'))
    user_profile = oauth_plugin.get_user_profile(token)

    if not user_profile:
        raise NotAuthenticatedError(error_msg='No user profile data returned')

    # Get the user from db
    method_uid = "{}:{}".format(oauth_plugin.name, user_profile.id)
    user = User.query\
        .filter(User.auth_methods.like("%{}%".format(method_uid)))\
        .one_or_none()
    if user is None:
        # Authenticated but not in the db; register a new Afterglow user if
        # allowed by plugin or the global config option
        register_users = oauth_plugin.register_users
        if register_users is None:
            register_users = app.config.get(
                'REGISTER_AUTHENTICATED_USERS', True)
        if not register_users:
            raise NotAuthenticatedError(
                error_msg='Automatic user registration disabled')

        user = User()
        user.username = None
        user.password = None
        user.first_name = user_profile.first_name if user_profile.first_name \
            else None
        user.last_name = user_profile.last_name if user_profile.last_name \
            else None
        user.email = user_profile.email if user_profile.email else None
        user.auth_methods = method_uid
        user.roles = [Role.query.filter_by(name='user').one()]
        try:
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    next_url = state.get('next')
    if not next_url:
        next_url = '/'
    expires_delta = app.config.get('ACCESS_TOKEN_EXPIRES')
    access_token = create_token(
        user.id, expires_delta, dict(method=oauth_plugin.name))
    return set_access_cookies(redirect(next_url), access_token)


@app.route('/oauth2/consent', methods=['GET', 'POST'])
@auth_required(allow_redirect=True)
def oauth2_consent():
    client_id = request.args.get('client_id')
    if not client_id:
        raise MissingFieldError('client_id')

    if client_id not in oauth_clients:
        raise UnknownClientError(id=client_id)

    client = oauth_clients[client_id]

    if request.method == 'GET':
        return render_template(
            'users/consent.html.j2', oauth_client=client,
            next_url=request.args.get('next'))

    try:
        uc = UserClient()
        uc.client_id = client.client_id
        uc.user_id = request.user.id
        db.session.add(uc)
        db.session.flush()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    else:
        return json_response('', 201)
