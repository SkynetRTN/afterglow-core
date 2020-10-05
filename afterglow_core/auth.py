"""
Afterglow Core: user authentication

All endpoints that assume authorized access must be decorated with
@auth_required; its explicit equivalent is :func:`authorize`.

User authentication is based on the access tokens. The user's access token (and,
optionally, refresh token and expiration time) is retrieved by making a request
to auth/login, which invokes a chain of authentication methods. All other
Afterglow resources require a valid access token supplied in the Authorization
HTTP header.

If user authentication is enabled in the app configuration (non-empty
USER_AUTH), the module also provides the endpoint for user management.
See :func:`admin_users` for request specs. Registered auth plugins can be
retrieved via :func:`auth_plugins` associated with the "auth" endpoint.
"""

import secrets
import os
import errno
from datetime import timedelta
from functools import wraps
import time
from typing import Callable, Optional, Sequence, Union

from flask import Response, request, make_response, redirect, url_for

from . import app
from .errors.auth import NotAuthenticatedError
from .resources.users import (
    AnonymousUser, DbPersistentToken, DbUser, user_datastore)
from .oauth2 import Token, memory_session


__all__ = [
    'oauth_plugins', 'auth_required', 'authenticate', 'security',
    'current_user', 'anonymous_user', 'jwt_manager',
    'set_access_cookies', 'clear_access_cookies',
]


# Read/create secret key
keyfile = os.path.join(
    os.path.abspath(app.config['DATA_ROOT']), 'AFTERGLOW_CORE_KEY')
try:
    with open(keyfile, 'rb') as f:
        key = f.read()
except IOError:
    key = os.urandom(24)
    d = os.path.dirname(keyfile)
    if os.path.isfile(d):
        os.remove(d)
    try:
        os.makedirs(d)
    except OSError as _e:
        if _e.errno != errno.EEXIST:
            raise
    del d
    with open(keyfile, 'wb') as f:
        f.write(key)
app.config['SECRET_KEY'] = key
del f, key, keyfile


oauth_plugins = {}
http_auth_plugins = {}

security = None  # flask_security instance
anonymous_user = current_user = AnonymousUser()
jwt_manager = None

USER_REALM = 'Registered Afterglow Users Only'


# noinspection PyUnusedLocal
def authenticate(roles: Optional[Union[str, Sequence[str]]] = None) \
        -> AnonymousUser:
    """
    Perform user authentication and return a User object

    :param roles: list of authenticated user role IDs or a single role ID

    :return: database object for the authenticated user; raises
        :class:`AuthError` on authentication error
    """
    return anonymous_user


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
            authenticate(roles)

            # if not request.args.get('identity_confirmed') and \
            #         kwargs.get('confirm_identity'):
            #     # verify that the user wants to continue with the currently
            #     # authenticated user account
            #     next_url = request.base_url + request.query_string + \
            #         '&identity_confirmed'
            #     return redirect(url_for('confirm_identity', next=next_url))

        except NotAuthenticatedError:
            if kwargs.get('allow_redirect'):
                return redirect(url_for('login', next=request.url))
            raise

        try:
            result = fn(*args, **kw)

            # handle rendered responses which are strings
            if isinstance(result, str):
                result = make_response(result)

            # Update access cookie if present in request
            access_token = request.cookies.get('afterglow_core_access_token')

            if access_token:
                result = set_access_cookies(result, access_token=access_token)

            return result
        finally:
            # Close the possible data file db session; don't import at module
            # level because of a circular dependency
            from .resources import data_files
            # noinspection PyBroadException
            try:
                with data_files.data_files_engine_lock:
                    data_files.data_files_engine[
                        data_files.get_root(current_user.id)
                    ].remove()
            except Exception:
                pass

    return wrapper


# noinspection PyUnusedLocal
def set_access_cookies(response: Response, access_token: Optional[str] = None) \
        -> Response:
    """
    Set access cookies for browser access

    :param response: original Flask response object
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


def _init_auth() -> None:
    """Initialize multi-user mode with authentication plugins"""
    # To reduce dependencies, only import marshmallow, flask-security, and
    # flask-sqlalchemy if user auth is enabled
    # noinspection PyProtectedMember
    from flask import _request_ctx_stack
    from flask_security import Security, current_user as _current_user
    from .plugins import load_plugins
    from .auth_plugins import (
        AuthnPluginBase, OAuthServerPluginBase, HttpAuthPluginBase)

    # noinspection PyGlobalUndefined
    global oauth_plugins, http_auth_plugins, authenticate, security, \
        current_user, set_access_cookies, clear_access_cookies

    current_user = _current_user

    def _set_access_cookies(response: Response,
                            access_token: Optional[str] = None) -> Response:
        """
        Adds session authorization cookie.

        :param flask.Response response: Flask response object
        :param str | None access_token: optional access token provided
            by the client; if None, create access token automatically

        :return: Flask response
        """
        expires_in = app.config.get('COOKIE_TOKEN_EXPIRES_IN', 86400)
        sess = memory_session()
        if not access_token:
            # Generate a temporary in-memory token
            token = Token(
                token_type='cookie',
                access_token=secrets.token_hex(20),
                user_id=request.user.id,
            )
            sess.add(token)
        else:
            # Check that the token provided by the user exists and not expired
            token = sess.query(Token)\
                .filter_by(
                    access_token=access_token,
                    user_id=request.user.id,
                    token_type='cookie',
                    revoked=False)\
                .one_or_none()
            if not token or not token.active:
                return clear_access_cookies(response)

        token.expires_in = expires_in
        token.issued_at = time.time()
        sess.commit()

        response.set_cookie(
            'afterglow_core_access_token', value=token.access_token,
            max_age=expires_in,
            secure=False, httponly=False)

        return response

    set_access_cookies = _set_access_cookies

    def _clear_access_cookies(response: Response) -> Response:
        """
        Clears the access cookies

        See: https://medium.com/lightrail/getting-token-authentication-right-in-
        a-stateless-single-page-application-57d0c6474e3

        :param response: Flask response

        :return: Flask response with access token removed from cookies
        """
        response.set_cookie('afterglow_core_access_token', '', expires=0)

        return response

    clear_access_cookies = _clear_access_cookies

    def _authenticate(roles: Optional[Union[str, Sequence[str]]] = None) \
            -> DbUser:
        """
        Authenticate the user

        :param roles: list of authenticated user role IDs or a single role ID

        :return: database object for the authenticated user; raises
            :class:`AuthError` on authentication error
        """
        # If access token in HTTP Authorization header, verify and authorize.
        # otherwise, attempt to reconstruct token from cookies
        tokens = []
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
        sess = memory_session()
        for token_type, access_token in tokens:
            try:
                if token_type == 'personal':
                    # Should be an existing permanent token
                    token = DbPersistentToken.query.filter_by(
                        access_token=access_token,
                        token_type=token_type).one_or_none()
                else:
                    token = sess.query(Token).filter_by(
                        access_token=access_token,
                        # token_type=token_type,
                        revoked=False).one_or_none()
                if not token:
                    raise ValueError('Token does not exist')
                if not token.active:
                    raise ValueError('Token expired')

                user = token.user

                if user is None:
                    raise ValueError('Unknown user ID')
                if not user.active:
                    raise ValueError('The user is deactivated')

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
                if not any(user_role.name == role for user_role in user.roles):
                    raise NotAuthenticatedError(
                        error_msg='"{}" role required'.format(role))

        # Make the authenticated user object available via `current_user` and
        # request.user
        _request_ctx_stack.top.user = request.user = user

        return user

    authenticate = _authenticate

    # Load auth plugins
    authn_plugins = load_plugins(
        'authentication', 'auth_plugins', AuthnPluginBase,
        app.config.get('AUTH_PLUGINS', []))

    for name, plugin in authn_plugins.items():
        if isinstance(plugin, OAuthServerPluginBase):
            oauth_plugins[name] = plugin
        elif isinstance(plugin, HttpAuthPluginBase):
            http_auth_plugins[name] = plugin

    # Initialize security subsystem
    app.config.setdefault('SECURITY_TOKEN_MAX_AGE', None)
    app.config.setdefault('SECURITY_PASSWORD_HASH', 'sha512_crypt')
    app.config.setdefault('SECURITY_PASSWORD_SALT', 'afterglow-core')
    app.config.setdefault('SECURITY_DEFAULT_HTTP_AUTH_REALM', USER_REALM)
    app.config.setdefault('ACCESS_TOKEN_EXPIRES', timedelta(days=1))
    app.config.setdefault('REFRESH_TOKEN_EXPIRES', None)

    security = Security(app, user_datastore, register_blueprint=False)


if app.config.get('AUTH_ENABLED'):
    _init_auth()
