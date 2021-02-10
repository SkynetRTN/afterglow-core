"""
Afterglow Core: top-level and initialization routes
"""

import json

from flask import Response, request, render_template, redirect, url_for
from flask_security.utils import hash_password, verify_password

from .. import app, json_response
from ..auth import (
    auth_required, clear_access_cookies, oauth_plugins, authenticate,
    set_access_cookies)
from ..resources.users import DbUser, DbRole, DbIdentity, db
from ..schemas.api.v1 import UserSchema
from ..errors import ValidationError, MissingFieldError
from ..errors.auth import (
    HttpAuthFailedError, NotInitializedError, UnknownAuthMethodError,
    NotAuthenticatedError, InitPageNotAvailableError)


__all__ = []


@app.route('/', methods=['GET'])
@auth_required(allow_redirect=True)
def default() -> Response:
    """
    Homepage for Afterglow Core

    GET /
        - Homepage/Dashboard

    :return: Afterglow Core homepage
    """
    return render_template('index.html.j2', current_user=request.user)


@app.route('/initialize', methods=['GET', 'POST'])
def initialize() -> Response:
    """
    Afterglow Core initialization

    GET /initialize
        - render initialization page

    POST /initialize
        - create admin user

    :return::
        GET: initialization page HTML
        POST: JSON-serialized :class:`UserSchema`
    """
    if DbUser.query.count() != 0:
        raise InitPageNotAvailableError()

    if request.method == 'GET':
        return render_template('initialize.html.j2')

    if request.method == 'POST':
        username = request.args.get('username')
        if not username:
            raise MissingFieldError('username')

        password = request.args.get('password')
        if not password:
            raise MissingFieldError('password')
        # TODO check security of password

        try:
            u = DbUser(
                username=username,
                password=hash_password(password),
                email=request.args.get('email'),
                first_name=request.args.get('first_name'),
                last_name=request.args.get('last_name'),
                birth_date=request.args.get('birth_date'),
                active=True,
                roles=[
                    DbRole.query.filter_by(name='admin').one(),
                    DbRole.query.filter_by(name='user').one(),
                ],
                settings=request.args.get('settings'),
            )
            db.session.add(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            return json_response(UserSchema().dump(u), 201)


# @app.route('/confirm_identity', methods=['GET', 'POST'])
# @auth_required(allow_redirect=True)
# def confirm_identity() -> Response:
#     """
#     Confirm identity before proceeding
#
#     GET|POST /confirm_identity
#         - confirm identity: verify that the client wants to continue
#           as the currently authorized user or switch accounts
#
#     :return:
#     """
#     next_url = request.args.get('next')
#     if not next_url:
#         next_url = url_for('default')
#
#     if request.method == 'GET':
#         return render_template(
#             'confirm_identity.html.j2',
#             next_url=next_url)
#
#     username = request.args.get('username')
#     if not username:
#         raise ValidationError('username', 'Username cannot be empty')
#
#     password = request.args.get('password')
#     if not password:
#         raise ValidationError('password', 'Password cannot be empty')
#
#     user = User.query.filter_by(username=username).one_or_none()
#     if user is None:
#         raise HttpAuthFailedError()
#
#     if not verify_password(password, user.password):
#         raise HttpAuthFailedError()
#
#     # set token cookies
#     request.user = user
#
#     return set_access_cookies(json_response())


@app.route('/login', methods=['GET', 'POST'])
def login() -> Response:
    """
    Login to Afterglow

    GET|POST /auth/login
        - login to Afterglow; authentication required using any of the methods
          defined in USER_AUTH

    :return: empty response with "afterglow_core_access_token" cookie
        if successfully logged in
    """
    # TODO Ensure CORS is disabled for POSTS to this endpoint
    # TODO Allow additional domains for cookies to be specified in server config

    next_url = request.args.get('next')
    if not next_url:
        next_url = url_for('default')

    if request.method == 'GET':
        try:
            authenticate()
            return redirect(next_url)
        except NotAuthenticatedError:
            pass

    # Do not allow login if Afterglow Core has not yet been configured
    if DbUser.query.count() == 0:
        return redirect(url_for('initialize'))

        # raise NotInitializedError()

    if request.method == 'GET':
        return render_template(
            'login.html.j2', oauth_plugins=oauth_plugins.values(),
            next_url=next_url)

    username = request.args.get('username')
    if not username:
        raise ValidationError('username', 'Username cannot be empty')

    password = request.args.get('password')
    if not password:
        raise ValidationError('password', 'Password cannot be empty')

    user = DbUser.query.filter_by(username=username).one_or_none()
    if user is None:
        raise HttpAuthFailedError()

    if not verify_password(password, user.password):
        raise HttpAuthFailedError()

    # set token cookies
    request.user = user

    return set_access_cookies(json_response())


@app.route('/login/oauth2/<string:plugin_id>')
def oauth2_authorized(plugin_id: str) -> Response:
    """
    OAuth2.0 authorization code granted redirect endpoint

    :param plugin_id: OAuth2 plugin ID

    :return: redirect to original request URL
    """
    # Do not allow login if Afterglow Core has not yet been configured
    if DbUser.query.count() == 0:
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
    user_profile = oauth_plugin.get_user(token)

    if not user_profile:
        raise NotAuthenticatedError(error_msg='No user profile data returned')

    # Get the user from db
    identity = DbIdentity.query \
        .filter_by(auth_method=oauth_plugin.name, name=user_profile['id']) \
        .one_or_none()
    if identity is None and oauth_plugin.name == 'skynet':
        # A workaround for migrating the accounts of users registered in early
        # versions that used Skynet usernames instead of IDs; a potential
        # security issue is a Skynet user with a numeric username matching
        # some other user's Skynet user ID
        identity = DbIdentity.query \
            .filter_by(auth_method=oauth_plugin.name,
                       name=user_profile['username']) \
            .one_or_none()
        if identity is not None:
            # First login via Skynet after migration: replace Identity.name =
            # username with user ID to prevent a possible future account seizure
            try:
                identity.name = user_profile['id']
                identity.data = user_profile
                identity.user.first_name = \
                    user_profile.get('first_name') or None
                identity.user.last_name = user_profile.get('last_name') or None
                identity.user.email = user_profile.get('email') or None
                identity.user.birth_date = \
                    user_profile.get('birth_date') or None
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
    if identity is None:
        # Authenticated but not in the db; register a new Afterglow user if
        # allowed by plugin or the global config option
        register_users = oauth_plugin.register_users
        if register_users is None:
            register_users = app.config.get(
                'REGISTER_AUTHENTICATED_USERS', True)
        if not register_users:
            raise NotAuthenticatedError(
                error_msg='Automatic user registration disabled')

        try:
            # By default, Afterglow username becomes the same as the OAuth
            # provider username; if empty or such user already exists, also try
            # email, full name, and id
            username = None
            for username_candidate in (
                    user_profile.get('username'),
                    user_profile.get('email'),
                    ' '.join(
                        ([user_profile['first_name']]
                         if user_profile.get('first_name') else []) +
                        ([user_profile['last_name']]
                         if user_profile.get('last_name') else [])),
                    user_profile['id']):
                if username_candidate and str(username_candidate).strip() and \
                        not DbUser.query.filter(
                            db.func.lower(DbUser.username) ==
                            username_candidate.lower()).count():
                    username = username_candidate
                    break
            user = DbUser(
                username=username or None,
                first_name=user_profile.get('first_name') or None,
                last_name=user_profile.get('last_name') or None,
                email=user_profile.get('email') or None,
                birth_date=user_profile.get('birth_date') or None,
                roles=[DbRole.query.filter_by(name='user').one()],
            )
            db.session.add(user)
            db.session.flush()
            identity = DbIdentity(
                user_id=user.id,
                name=user_profile['id'],
                auth_method=oauth_plugin.name,
                data=user_profile,
            )
            db.session.add(identity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    else:
        user = identity.user
        if identity.data != user_profile:
            # Account data (e.g. API access token) has changed since the last
            # login, update it
            try:
                identity.data = user_profile
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    next_url = state.get('next')
    if not next_url:
        next_url = '/'
    request.user = user
    return set_access_cookies(redirect(next_url))


@app.route('/logout', methods=['GET', 'POST'])
def logout() -> Response:
    """
    Logout from Afterglow

    GET|POST /auth/logout
        - log the current user out

    :return: empty JSON response
    """
    return clear_access_cookies(redirect(url_for('login')))
