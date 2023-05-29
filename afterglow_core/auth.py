"""
Afterglow Core: user authentication

All endpoints that assume authorized access must be decorated with
@auth_required; its explicit equivalent is :func:`authorize`.

User authentication is based on the access tokens. The user's access token
(and, optionally, refresh token and expiration time) is retrieved by making
a request to auth/login, which invokes a chain of authentication methods. All
other Afterglow resources require a valid access token supplied
in the Authorization HTTP header.

If user authentication is enabled in the app configuration (non-empty
USER_AUTH), the module also provides the endpoint for user management.
See :func:`admin_users` for request specs. Registered auth plugins can be
retrieved via :func:`auth_plugins` associated with the "auth" endpoint.
"""

import secrets
import os
from datetime import timedelta
from functools import wraps
import time
from urllib.parse import urlencode
from typing import Callable, Optional, Sequence, Union

from flask import Response, current_app, g, request, make_response, redirect
from flask_wtf.csrf import generate_csrf

from .auth_plugins import AuthnPluginBase
from .resources import users
from .errors.auth import NotAuthenticatedError
from . import json_response


__all__ = [
    'init_auth', 'oauth_plugins', 'auth_required', 'authenticate',
    'jwt_manager', 'set_access_cookies', 'clear_access_cookies', 'user_login',
]


oauth_plugins = {}
http_auth_plugins = {}

jwt_manager = None

USER_REALM = 'Registered Afterglow Users Only'


# noinspection PyUnusedLocal
def authenticate(roles: Optional[Union[str, Sequence[str]]] = None):
    """
    Perform user authentication

    :param roles: list of authenticated user role IDs or a single role ID

    :return: database object for the authenticated user; raises
        :class:`AuthError` on authentication error
    """
    from .resources.users import AnonymousUser
    user = g._login_user = request.user = AnonymousUser()
    return user


def _doublewrap(fn: Callable) -> Callable:
    """
    A decorator decorator, allowing the decorator to be used as:
        @decorator(with, arguments, and=kwargs)
    or
        @decorator
    """
    @wraps(fn)
    def new_dec(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # Actual decorated function
            return fn(args[0])
        else:
            # decorator arguments
            return lambda realf: fn(realf, *args, **kwargs)

    return new_dec


@_doublewrap
def auth_required(fn, *roles, **kwargs) -> Callable:
    """
    Decorator for resources that need authentication

    Usage:
        @auth_required
        def resource(...):
            ...
    or
        @auth_required('user')
    or
        @auth_required('user', 'admin')
    or
        @auth_required(allow_redirect=True)

    :param fn: function being decorated
    :param roles: one or multiple user role ID(s)
    :param kwargs::
        allow_redirect=True: redirect to login page if not authenticated

    :return: decorated resource
    """
    @wraps(fn)
    def wrapper(*args, **kw):
        try:
            user_id = authenticate(roles).id

            # if not request.args.get('identity_confirmed') and \
            #         kwargs.get('confirm_identity'):
            #     # verify that the user wants to continue with the currently
            #     # authenticated user account
            #     next_url = request.base_url + request.query_string + \
            #         '&identity_confirmed'
            #     return redirect(url_for('confirm_identity', next=next_url))

        except NotAuthenticatedError:
            if kwargs.get('allow_redirect'):
                dashboard_prefix = current_app.config.get("DASHBOARD_PREFIX")
                args = urlencode(dict(next=request.url))
                return redirect(
                    '{dashboard_prefix}/login?{args}'
                    .format(dashboard_prefix=dashboard_prefix, args=args))
            raise

        try:
            result = fn(*args, **kw)

            # handle rendered responses which are strings
            if isinstance(result, str):
                result = make_response(result)

            # Update access cookie if present in request
            access_token = request.cookies.get('afterglow_core_access_token')

            if access_token:
                result = set_access_cookies(
                    result, user_id, access_token=access_token)

            return result
        finally:
            # Close the possible data file db session; don't import at module
            # level because of a circular dependency
            from .resources import data_files
            # noinspection PyBroadException
            try:
                with data_files.data_file_thread_lock:
                    data_files.data_file_engine[
                        data_files.get_root(user_id), os.getpid()
                    ][1].remove()
            except Exception:
                pass

    return wrapper


# noinspection PyUnusedLocal
def set_access_cookies(response: Response, user_id: Optional[int] = None,
                       access_token: Optional[str] = None) -> Response:
    """
    Set access cookies for browser access

    :param response: original Flask response object
    :param user_id: authenticated user ID
    :param access_token: encoded access token; if None, create access token
        automatically

    :return: modified Flask response
    """
    return response


def clear_access_cookies(response: Response, **__) -> Response:
    """
    Clear access cookies for browser access

    :param response: original Flask response object

    :return: modified Flask response
    """
    return response


def user_login(user_profile: dict, auth_plugin: AuthnPluginBase) -> Response:
    """
    Called by auth plugins after the user has been authenticated

    :param user_profile: user profile dict as returned by the plugin's
        :method:`get_user`
    :param auth_plugin: auth plugin instance
    """
    if not user_profile:
        raise NotAuthenticatedError(error_msg='No user profile data returned')

    # Get the user from db
    identity = users.DbIdentity.query \
        .filter_by(auth_method=auth_plugin.name, name=user_profile['id']) \
        .one_or_none()
    if identity is None and auth_plugin.name == 'skynet':
        # A workaround for migrating the accounts of users registered in early
        # versions that used Skynet usernames instead of IDs; a potential
        # security issue is a Skynet user with a numeric username matching
        # some other user's Skynet user ID
        identity = users.DbIdentity.query \
            .filter_by(auth_method=auth_plugin.name,
                       name=user_profile['username']) \
            .one_or_none()
        if identity is not None:
            # First login via Skynet after migration: replace Identity.name =
            # username with user ID to prevent a possible future account
            # seizure
            try:
                identity.name = user_profile['id']
                identity.data = user_profile
                identity.user.first_name = \
                    user_profile.get('first_name') or None
                identity.user.last_name = user_profile.get('last_name') or None
                identity.user.email = user_profile.get('email') or None
                identity.user.birth_date = \
                    user_profile.get('birth_date') or None
                users.db.session.commit()
            except Exception:
                users.db.session.rollback()
                raise

    if identity is None:
        # Authenticated but not in the db; look for identities with the same
        # email and link accounts if found
        email = user_profile.get('email').lower()
        if email:
            for user in users.DbUser.query:
                if user.email and user.email.lower() == email:
                    # Add another identity to the existing user account
                    try:
                        identity = users.DbIdentity(
                            user_id=user.id,
                            name=user_profile['id'],
                            auth_method=auth_plugin.name,
                            data=user_profile,
                        )
                        users.db.session.add(identity)
                        users.db.session.commit()
                    except Exception:
                        users.db.session.rollback()
                        raise
                    break

    if identity is None:
        # Register a new Afterglow user if allowed by plugin or the global
        # config option
        register_users = auth_plugin.register_users
        if register_users is None:
            register_users = current_app.config.get(
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
                        not users.DbUser.query.filter(
                            users.db.func.lower(users.DbUser.username) ==
                            username_candidate.lower()).count():
                    username = username_candidate
                    break
            user = users.DbUser(
                username=username or None,
                first_name=user_profile.get('first_name') or None,
                last_name=user_profile.get('last_name') or None,
                email=user_profile.get('email') or None,
                roles=[users.DbRole.query.filter_by(name='user').one()],
            )
            users.db.session.add(user)
            users.db.session.flush()
            identity = users.DbIdentity(
                user_id=user.id,
                name=user_profile['id'],
                auth_method=auth_plugin.name,
                data=user_profile,
            )
            users.db.session.add(identity)
            users.db.session.commit()
        except Exception:
            users.db.session.rollback()
            raise
    else:
        user = identity.user
        if identity.data != user_profile:
            # Account data (e.g. API access token) has changed since the last
            # login, update it
            try:
                identity.data = user_profile
                users.db.session.commit()
            except Exception:
                users.db.session.rollback()
                raise

    g._login_user = request.user = user
    return set_access_cookies(json_response(), user.id)


def init_auth() -> None:
    """Initialize multi-user mode with authentication plugins"""
    # To reduce dependencies, only import marshmallow, flask-security, and
    # flask-sqlalchemy if user auth is enabled
    # noinspection PyProtectedMember
    from .plugins import load_plugins
    from .auth_plugins import (
        AuthnPluginBase, OAuthServerPluginBase, HttpAuthPluginBase)

    # noinspection PyGlobalUndefined
    global oauth_plugins, http_auth_plugins, authenticate, \
        set_access_cookies, clear_access_cookies

    def _set_access_cookies(response: Response, user_id: Optional[int] = None,
                            access_token: Optional[str] = None) -> Response:
        """
        Adds session authorization cookie.

        :param flask.Response response: Flask response object
        :param str | None access_token: optional access token provided
            by the client; if None, create access token automatically

        :return: Flask response
        """
        from .resources.users import Token, db
        expires_in = current_app.config.get('COOKIE_TOKEN_EXPIRES_IN', 86400)
        try:
            if not access_token:
                # Generate a new token
                access_token = secrets.token_hex(20)
                db.session.add(Token(
                    token_type='cookie',
                    access_token=access_token,
                    user_id=user_id,
                    expires_in=expires_in,
                    issued_at=time.time(),
                ))
                db.session.commit()
            else:
                # Check that the token provided by the user exists
                # and not expired
                token = Token.query \
                    .filter_by(
                        access_token=access_token,
                        user_id=user_id,
                        token_type='cookie') \
                    .one_or_none()
                if token is None or not token.active:
                    if token is not None:
                        # Delete revoked/expired tokens from the db
                        # noinspection PyBroadException
                        try:
                            db.session.delete(token)
                            db.session.commit()
                        except Exception:
                            db.session.rollback()
                    return clear_access_cookies(response)
        except Exception:
            db.session.rollback()
            raise

        csrf_token = generate_csrf()
        response.set_cookie('afterglow_core.csrf', csrf_token)

        response.set_cookie(
            'afterglow_core_access_token', value=access_token,
            max_age=expires_in, secure=False, httponly=False)

        response.set_cookie(
            'afterglow_core_user_id', value=str(user_id),
            max_age=expires_in, secure=False, httponly=False)

        return response

    set_access_cookies = _set_access_cookies

    def _clear_access_cookies(response: Response) -> Response:
        """
        Clears the access cookies

        See: https://medium.com/lightrail/getting-token-authentication-right-
        in-a-stateless-single-page-application-57d0c6474e3

        :param response: Flask response

        :return: Flask response with access token removed from cookies
        """
        response.set_cookie('afterglow_core_access_token', '', expires=0)
        response.set_cookie('afterglow_core_user_id', '', expires=0)
        response.set_cookie('afterglow_core.csrf', '', expires=0)

        return response

    clear_access_cookies = _clear_access_cookies

    def _authenticate(roles: Optional[Union[str, Sequence[str]]] = None):
        """
        Authenticate the user

        :param roles: list of authenticated user role IDs or a single role ID
        """
        from .resources import users

        # If access token in HTTP Authorization header, verify and authorize.
        # otherwise, attempt to reconstruct token from cookies
        tokens = []
        token_param = request.args.get('token', None)
        if token_param:
            tokens.append(('personal', token_param))

        token_hdr = request.headers.get('Authorization')
        if token_hdr:
            parts = token_hdr.split()
            if parts[0] == 'Bearer' and len(parts) == 2:
                tokens.append(('oauth2', parts[1]))
                tokens.append(('personal', parts[1]))

        access_token = request.cookies.get('afterglow_core_access_token')
        if access_token:
            tokens.append(('cookie', access_token))

        if not tokens:
            raise NotAuthenticatedError(
                error_msg='Missing authentication token')

        user = None
        error_msgs = []
        user_roles = []
        for token_type, access_token in tokens:
            try:
                if token_type == 'personal':
                    # Should be an existing permanent token
                    token = users.DbPersistentToken.query.filter_by(
                        access_token=access_token,
                        token_type=token_type).one_or_none()
                else:
                    token = users.Token.query.filter_by(
                        access_token=access_token,
                        access_token_revoked_at=0).one_or_none()
                if token is None:
                    raise ValueError('Token does not exist')
                if not token.active:
                    raise ValueError('Token revoked or expired')

                user = token.user

                if user is None:
                    raise ValueError('Unknown user ID')
                if not user.active:
                    raise ValueError('The user is deactivated')

                user_roles = [user_role.name for user_role in user.roles]
            except Exception as e:
                error_msgs.append('{} (type: {})'.format(e, token_type))
            else:
                break

        if user is None:
            raise NotAuthenticatedError(error_msg='. '.join(error_msgs))

        # Check roles
        if roles:
            if isinstance(roles, str):
                roles = roles.split(',')
            for role in roles:
                role = role.strip()
                if role not in user_roles:
                    raise NotAuthenticatedError(
                        error_msg='"{}" role required'.format(role))

        # Make the authenticated user object available via `current_user`
        g._login_user = request.user = user
        return user

    authenticate = _authenticate

    # Load auth plugins
    authn_plugins = load_plugins(
        'authentication', 'auth_plugins', AuthnPluginBase,
        current_app.config.get('AUTH_PLUGINS', []))

    for name, plugin in authn_plugins.items():
        if isinstance(plugin, OAuthServerPluginBase):
            oauth_plugins[name] = plugin
        elif isinstance(plugin, HttpAuthPluginBase):
            http_auth_plugins[name] = plugin

    # Initialize security subsystem
    current_app.config.setdefault('SECURITY_TOKEN_MAX_AGE', None)
    current_app.config.setdefault('SECURITY_PASSWORD_HASH', 'sha512_crypt')
    current_app.config.setdefault('SECURITY_PASSWORD_SALT', 'afterglow-core')
    current_app.config.setdefault(
        'SECURITY_DEFAULT_HTTP_AUTH_REALM', USER_REALM)
    current_app.config.setdefault('ACCESS_TOKEN_EXPIRES', timedelta(days=1))
    current_app.config.setdefault('REFRESH_TOKEN_EXPIRES', None)
