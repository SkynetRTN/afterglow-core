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

from __future__ import absolute_import, division, print_function

import os
import errno
import uuid
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import request, make_response, redirect, url_for

from . import app
from .errors.auth import NotAuthenticatedError
from .users import AnonymousUser, Role, User, user_datastore


__all__ = [
    'oauth_plugins', 'auth_required', 'authenticate', 'security',
    'current_user', 'anonymous_user', 'jwt_manager', 'create_token',
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
def authenticate(roles=None, request_type='access'):
    """
    Perform user authentication using the given methods

    :param roles: list of authenticated user role IDs or a single role ID
    :param str request_type: JWT type to expect: "access" (for most resources)
        or "refresh" (for auth/refresh)

    :return: database object for the authenticated user; raises
        :class:`AuthError` on authentication error
    :rtype: afterglow_core.users.User
    """
    return anonymous_user


def _doublewrap(fn):
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
def auth_required(fn, *roles, **kwargs):
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
        @auth_required(request_type='refresh')

    :param callable fn: function being decorated
    :param roles: one or multiple user role ID(s)
    :param kwargs::
        request_type: JWT type to expect: "access" (for most resources, default)
            or "refresh" (for auth/refresh)

    :return: decorated resource
    """
    @wraps(fn)
    def wrapper(*args, **kw):
        try:
            authenticate(roles, **kwargs)
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
            token_sig = request.cookies.get('afterglow_core_access_token_sig')
            token_hdr_payload = request.cookies.get('afterglow_core_access_token')
            if token_sig and token_hdr_payload:
                result = set_access_cookies(
                    result, token_hdr_payload + '.' + token_sig)

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


def encode_jwt(additional_token_data, expires_delta):
    """
    Creates a JWT with the optional user data

    :param dict additional_token_data: additional data to add to the JWT
    :param datetime.datetime expires_delta: token expiration time;
        False = never expire

    :return: encoded JWT
    :rtype: str
    """
    now = datetime.utcnow()
    token_data = {
        'iat': now,
        'nbf': now,
        'jti': str(uuid.uuid4()),
    }

    # If expires_delta is False, the JWT should never expire
    # and the 'exp' claim is not set.
    if expires_delta:
        token_data['exp'] = now + expires_delta

    token_data.update(additional_token_data)
    return jwt.encode(
        token_data, app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')


def decode_jwt(encoded_token):
    """
    Decodes an encoded JWT

    :param str encoded_token: The encoded JWT string to decode

    :return: dictionary containing contents of the JWT
    :rtype: dict
    """
    # This call verifies the ext, iat, and nbf claims
    data = jwt.decode(
        encoded_token, app.config['SECRET_KEY'], algorithms=['HS256'])

    # Make sure that any custom claims we expect in the token are present
    if 'jti' not in data:
        raise NotAuthenticatedError(error_msg='Missing claim: jti')
    if 'identity' not in data:
        raise NotAuthenticatedError(
            error_msg='Missing claim: {}'.format('identity'))
    if 'type' not in data or data['type'] not in ('refresh', 'access'):
        raise NotAuthenticatedError(
            error_msg='Missing or invalid claim: type')
    if data['type'] == 'access':
        if 'user_claims' not in data:
            data['user_claims'] = {}

    return data


def create_token(identity, expires_delta=None, user_claims=None,
                 token_type='access'):
    """
    Creates a new encoded (utf-8) access or refresh token.

    :param identity: identifier for who this token is for (ex, username);
        must be json serializable.
    :param datetime.timedelta expires_delta: how far in the future this
        token should expire (set to False to disable expiration)
    :param dict user_claims: custom claims to include in this token; must be
        json serializable
    :param str token_type: token type: "access" or "refresh"

    :return: encoded access/refresh token
    :rtype: str
    """
    token_data = {
        'identity': identity,
        'type': token_type,
    }

    # Don't add extra data to the token if user_claims is empty.
    if user_claims:
        token_data['user_claims'] = user_claims

    return encode_jwt(token_data, expires_delta)


def set_access_cookies(*_, **__):
    """
    Set access cookies for browser access

    :return: response
    :rtype: flask.response

    """
    return


def clear_access_cookies(*_, **__):
    """
    Clear access cookies for browser access

    :return: response
    :rtype: flask.response

    """
    return


def init_auth():
    """Initialize multi-user mode with authentication plugins"""
    # To reduce dependencies, only import marshmallow, flask-security, and
    # flask-sqlalchemy if user auth is enabled
    # noinspection PyProtectedMember
    from flask import _request_ctx_stack
    from flask_security import Security, current_user as _current_user
    from .plugins import load_plugins
    from .auth_plugins import AuthnPluginBase, OAuthServerPluginBase, HttpAuthPluginBase

    # noinspection PyGlobalUndefined
    global oauth_plugins, http_auth_plugins, authenticate, security, current_user, \
        set_access_cookies, clear_access_cookies

    current_user = _current_user

    def _set_access_cookies(response, access_token=None):
        """
        Adds two new cookies to response. The signature cookie is HTTP-Only (not
        accessible to the client-side JS and expires with the session. The
        second cookie contains the access token header and payload and expires
        after configured idle period.

        See: https://medium.com/lightrail/getting-token-authentication-right-
        in-a-stateless-single-page-application-57d0c6474e3

        :param flask.Response response: Flask response object
        :param str | None access_token: encoded access token; if None, create
            access token automatically

        :return: Flask response
        :rtype: flask.Response
        """

        expires_delta = app.config.get('ACCESS_TOKEN_EXPIRES')
        if not access_token:
            method = _request_ctx_stack.top.auth_method
            access_token = create_token(
                current_user.id, expires_delta, dict(method=method))

        hdr_payload, signature = access_token.rsplit('.', 1)
        response.set_cookie(
            'afterglow_core_access_token', value=hdr_payload,
            max_age=expires_delta.total_seconds() if expires_delta else None,
            secure=False, httponly=False)
        response.set_cookie(
            'afterglow_core_access_token_sig', value=signature, max_age=None, secure=False,
            httponly=True)

        return response

    set_access_cookies = _set_access_cookies

    def _clear_access_cookies(response):
        """
        Clears the access cookies

        See: https://medium.com/lightrail/getting-token-authentication-right-in-
        a-stateless-single-page-application-57d0c6474e3

        :param response: Flask response

        :return: Flask response with access token removed from cookies
        :rtype: flask.Response
        """
        response.set_cookie('afterglow_core_access_token_sig', '', expires=0)
        response.set_cookie('afterglow_core_access_token', '', expires=0)

        return response

    clear_access_cookies = _clear_access_cookies

    def _authenticate(roles=None, request_type='access', **__):
        """
        Authenticate the user

        :param str | list[str] roles: list of authenticated user role IDs
            or a single role ID
        :param str request_type: JWT type to expect: "access" (for most
            resources) or "refresh" (for auth/refresh)

        :return: database object for the authenticated user; raises
            :class:`AuthError` on authentication error
        :rtype: afterglow_core.users.User
        """
        # If access token in HTTP Authorization header, verify and authorize.
        # otherwise, attempt to reconstruct token from cookies
        tokens = []
        token_hdr = request.headers.get('Authorization')
        if token_hdr:
            parts = token_hdr.split()
            if parts[0] == 'Bearer' and len(parts) == 2:
                tokens.append(('headers', parts[1]))

        token_sig = request.cookies.get('afterglow_core_access_token_sig')
        token_hdr_payload = request.cookies.get('afterglow_core_access_token')
        if token_sig and token_hdr_payload:
            tokens.append(('cookies', token_hdr_payload + '.' + token_sig))

        if not tokens:
            raise NotAuthenticatedError(
                error_msg='Missing authentication token')

        user = None
        error_msgs = []
        for token_source, token in tokens:
            try:
                token_decoded = decode_jwt(token)

                if token_decoded.get('type') != request_type:
                    raise ValueError('Expected {} token'.format(request_type))

                user_id = token_decoded.get('identity')
                if not user_id:
                    raise ValueError('Missing username')

                # Make the user's auth method available via the request context
                # stack
                method = token_decoded.get('user_claims', {}).get('method')
                if method:
                    _request_ctx_stack.top.auth_method = method

                # Get the user from db
                user = User.query.filter_by(id=user_id).one_or_none()
                if user is None:
                    raise ValueError('Unknown username')
                if not user.active:
                    raise ValueError('The user is deactivated')

                # Check roles if any
                if roles:
                    if isinstance(roles, str) or isinstance(roles, type(u'')):
                        roles = [roles]
                    for role in roles:
                        if not Role.query.filter_by(
                                name=role).one_or_none() in user.roles:
                            raise ValueError('"{}" role required'.format(role))
            except Exception as e:
                error_msgs.append('{} (source: {})'.format(e, token_source))
            else:
                break

        if user is None:
            raise NotAuthenticatedError(error_msg='. '.join(error_msgs))

        # Make the authenticated user object available via `current_user` and
        # request.user
        _request_ctx_stack.top.user = request.user = user

        return user

    authenticate = _authenticate

    # Load auth plugins
    authn_plugins = load_plugins(
        'authentication', 'auth_plugins', AuthnPluginBase,
        app.config['AUTH_PLUGINS'])

    for name, plugin in authn_plugins.items():
        if isinstance(plugin, OAuthServerPluginBase): oauth_plugins[name] = plugin
        elif isinstance(plugin, HttpAuthPluginBase): http_auth_plugins[name] = plugin
        

    # Initialize security subsystem
    app.config.setdefault('SECURITY_TOKEN_MAX_AGE', None)
    app.config.setdefault('SECURITY_PASSWORD_HASH', 'sha512_crypt')
    app.config.setdefault('SECURITY_PASSWORD_SALT', 'afterglow-core')
    app.config.setdefault('SECURITY_DEFAULT_HTTP_AUTH_REALM', USER_REALM)
    app.config.setdefault('ACCESS_TOKEN_EXPIRES', timedelta(days=1))
    app.config.setdefault('REFRESH_TOKEN_EXPIRES', None)

    security = Security(app, user_datastore, register_blueprint=False)
