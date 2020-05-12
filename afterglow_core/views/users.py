"""
Afterglow Core: login and user account management routes
"""

import os
import shutil
import json

# noinspection PyProtectedMember
from flask import _request_ctx_stack
from flask_security.utils import hash_password, verify_password
from flask import redirect, request, render_template, url_for

from .. import app, json_response
from ..auth import (
    auth_required, create_token, clear_access_cookies, set_access_cookies,
    oauth_plugins)
from ..oauth2 import oauth_clients
from ..users import Role, User, UserClient, db
from ..models.user import UserSchema
from ..errors import MissingFieldError, ValidationError
from ..errors.auth import (
    AdminRequiredError, UnknownUserError, CannotDeactivateTheOnlyAdminError,
    DuplicateUsernameError, HttpAuthFailedError, CannotDeleteCurrentUserError,
    NotInitializedError, NotAuthenticatedError, LocalAccessRequiredError,
    UnknownAuthMethodError)
from ..errors.oauth2 import UnknownClientError, MissingClientIdError


@app.route('/users/login', methods=['GET', 'POST'])
def login():
    """
    Login to Afterglow

    GET|POST /auth/login
        - login to Afterglow; authentication required using any of the methods
          defined in USER_AUTH

    GET|POST /auth/login/[method]
        - login using the given auth method ID (see GET /auth/methods)

    :return: JSON {"access_token": "token", "refresh_token": token}
    :rtype: flask.Response
    """
    # TODO Ensure CORS is disabled for POSTS to this endpoint
    # TODO Allow additional domains for cookies to be specified in server config

    # Do not allow login if Afterglow Core has not yet been configured
    if User.query.count() == 0:
        if app.config.get('REMOTE_ADMIN') or request.remote_addr == '127.0.0.1':
            return redirect(url_for('initialize'))

        raise NotInitializedError()

    next_url = request.args.get('next')
    if not next_url:
        next_url = '/'

    if request.method == 'GET':
        return render_template(
            'users/login.html.j2', oauth_plugins=oauth_plugins.values(),
            next_url=next_url)

    username = request.args.get('username')
    if not username:
        raise ValidationError('username', 'Username cannot be empty')

    password = request.args.get('password')
    if not password:
        raise ValidationError('password', 'Password cannot be empty')

    user = User.query.filter(User.username == username).one_or_none()
    if not user:
        raise HttpAuthFailedError()

    if not verify_password(password, user.password):
        raise HttpAuthFailedError()

    method = 'http'

    # user = security.login_manager._request_callback(request)
    # if not user or user.is_anonymous:
    #     # Check basic auth
    #     authorization = request.authorization
    #     if authorization:
    #         user = auth.security.datastore.find_user(
    #             username=authorization.username)
    #         if user and not user.is_anonymous and not verify_password(
    #                 authorization.password, user.password):
    #             raise HttpAuthFailedError()
    # if not user or user.is_anonymous:
    #     raise HttpAuthFailedError()

    # set token cookies
    expires_delta = app.config.get('ACCESS_TOKEN_EXPIRES')
    access_token = create_token(
        user.id, expires_delta, dict(method=method))

    return set_access_cookies(json_response(dict()), access_token)


@app.route('/users/logout', methods=['GET', 'POST'])
def logout():
    """
    Logout from Afterglow

    GET|POST /auth/logout
        - log the current user out

    :return: empty JSON response
    :rtype: flask.Response
    """
    return clear_access_cookies(redirect(url_for('login')))


# Register OAuth2.0 authorization code redirect handler
@app.route('/users/oauth2/<string:plugin_id>')
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


@app.route('/users/oauth2/consent', methods=['GET', 'POST'])
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

@app.route('/users/token', methods=['GET', 'POST'])
@auth_required
def user_token():
    """
    Return access and refresh tokens for the currently logged in user

    :return: JSON object {"access_token": ..., "refresh_token": ...}
    :rtype: flask.Response
    """
    method = _request_ctx_stack.top.auth_method
    return json_response({
        'access_token': create_token(
            request.user.id, app.config.get('ACCESS_TOKEN_EXPIRES'),
            dict(method=method)),
        'refresh_token': create_token(
            request.user.id, app.config.get('REFRESH_TOKEN_EXPIRES'),
            dict(method=method), 'refresh'),
    })
