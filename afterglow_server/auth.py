"""
Afterglow Access Server: user authentication

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
import shutil
from datetime import datetime, timedelta
from functools import wraps
from flask import request
from werkzeug.exceptions import HTTPException
from . import app, errors, json_response, url_prefix
from .users import AnonymousUser, Role, User, UserSchema, db, user_datastore


__all__ = [
    'auth_plugins', 'auth_required', 'authenticate', 'security',
    'current_user', 'anonymous_user', 'jwt_manager',
    'AuthError', 'NotAuthenticatedError', 'NoAdminRegisteredError',
    'RoleRequiredError', 'AdminRequiredError', 'AdminOrSameUserRequiredError',
    'UnknownUserError', 'InactiveUserError', 'RemoteAdminDisabledError',
    'CannotDeactivateTheOnlyAdminError', 'DuplicateUsernameError',
    'UnknownAuthMethodError',
]


class AuthError(errors.AfterglowError):
    """
    Base class for all Afterglow authentication errors
    """
    pass


class NotAuthenticatedError(AuthError):
    """
    User authentication failed, access denied

    Extra attributes::
        None
    """
    code = 401
    subcode = 100
    message = 'Not authenticated'


class NoAdminRegisteredError(AuthError):
    """
    Attempt to manage users (except for adding admin during the initial setup)
    with no admins registered in the system

    Extra attributes::
        None
    """
    code = 403
    subcode = 101
    message = 'No admins registered'


class RoleRequiredError(AuthError):
    """
    Authenticated user does not have the required role to access the resource

    Extra attributes::
        role: required role name
    """
    code = 403
    subcode = 102
    message = 'Missing required role'


class AdminRequiredError(AuthError):
    """
    Request needs authentication with admin role

    Extra attributes::
        None
    """
    code = 403
    subcode = 103
    message = 'Must be admin to do that'


class AdminOrSameUserRequiredError(AuthError):
    """
    Request needs authentication with admin role or the same user it refers to

    Extra attributes::
        None
    """
    code = 403
    subcode = 104
    message = 'Must be admin or same user to do that'


class UnknownUserError(AuthError):
    """
    User with the given ID is not registered

    Extra attributes::
        id: user ID
    """
    code = 404
    subcode = 105
    message = 'Unknown user'


class InactiveUserError(errors.AfterglowError):
    """
    Attempting to access Afterglow using an inactive user account

    Extra attributes::
        None
    """
    code = 403
    subcode = 106
    message = 'The user is deactivated'


class RemoteAdminDisabledError(AuthError):
    """
    Attempt to access /admin from non-local host

    Extra attributes::
        None
    """
    code = 403
    subcode = 107
    message = 'Remote administration not allowed'


class CannotDeactivateTheOnlyAdminError(AuthError):
    """
    Deactivating, removing admin role, or deleting the only admin user
    in the system

    Extra attributes::
        None
    """
    code = 403
    subcode = 108
    message = 'Cannot deactivate/delete the only admin in the system'


class DuplicateUsernameError(AuthError):
    """
    Attempting to register user with username that is already associated with
    some other user

    Extra attributes::
        username: duplicate username
    """
    code = 403
    subcode = 109
    message = 'User with this username already exists'


class UnknownAuthMethodError(AuthError):
    """
    Auth method was requested that is not registered in USER_AUTH

    Extra attributes::
        method: auth method ID
    """
    code = 403
    subcode = 110
    message = 'Unknown authentication method'


# Read/create secret key
keyfile = os.path.join(
    os.path.abspath(app.config['DATA_ROOT']), 'AFTERGLOW_SERVER_KEY')
try:
    with open(keyfile, 'rb') as f:
        key = f.read()
except IOError:
    key = os.urandom(24)
    d = os.path.dirname(keyfile)
    if os.path.isfile(d):
        os.remove(d)
    if not os.path.exists(d):
        try:
            os.makedirs(d)
        except IOError as _e:
            if _e.errno != errno.EEXIST:
                raise
    del d
    with open(keyfile, 'wb') as f:
        f.write(key)
app.config['SECRET_KEY'] = key
del f, key, keyfile


auth_plugins = {}

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
    :rtype: afterglow_server.users.User
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
        authenticate(roles, **kwargs)
        return _refresh_access_cookies(fn(*args, **kw))

    return wrapper


def _create_token(*_, **__):
    """
    Create a JWT

    :return: JWT
    :rtype: str
    """
    return ''


def _set_access_cookies(*_, **__):
    """
    Set access cookies for browser access

    :return: response
    :rtype: flask.response

    """
    return


def _refresh_access_cookies(*_, **__):
    """
    Refresh access cookies for browser access

    :return: response
    :rtype: flask.response

    """
    return


def _clear_access_cookies(*_, **__):
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
    import uuid
    import jwt
    # noinspection PyProtectedMember
    from flask import _request_ctx_stack
    from flask_security import Security, current_user as _current_user
    from flask_security.utils import hash_password
    from .plugins import load_plugins
    from .auth_plugins import AuthPlugin

    # noinspection PyGlobalUndefined
    global auth_plugins, authenticate, security, current_user, _create_token, \
        _set_access_cookies, _refresh_access_cookies, _clear_access_cookies

    current_user = _current_user

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
            token_data, app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

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

    def __create_token(identity, expires_delta=None, user_claims=None,
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

    _create_token = __create_token

    def __set_access_cookies(response, access_token):
        """
        Adds two new cookies to response. The signature cookie is HTTP-Only (not
        accessible to the client-side JS and expires with the session. The
        second cookie contains the access token header and payload and expires
        after configured idle period.

        See: https://medium.com/lightrail/getting-token-authentication-right-
        in-a-stateless-single-page-application-57d0c6474e3

        :param flask.Response response: Flask response object
        :param str access_token: encoded access token

        :return: Flask response
        :rtype: flask.Response
        """
        signature = access_token.split('.')[2]
        response.set_cookie(
            'access_token_sig', value=signature, max_age=None, secure=False,
            httponly=True)

        hdr_payload = '.'.join(access_token.split('.')[:2])
        response.set_cookie(
            'access_token', value=hdr_payload,
            max_age=app.config['ACCESS_TOKEN_COOKIE_EXPIRES'].total_seconds(),
            secure=False, httponly=False)

        return response

    _set_access_cookies = __set_access_cookies

    def __refresh_access_cookies(response):
        """
        Refreshes the access cookies

        See: https://medium.com/lightrail/getting-token-authentication-right-in-
        a-stateless-single-page-application-57d0c6474e3

        :param response: Flask response
        :return: Flask response
        """
        token_sig = request.cookies.get('access_token_sig')
        token_hdr_payload = request.cookies.get('access_token')
        if token_sig and token_hdr_payload:
            token = token_hdr_payload + '.' + token_sig
            response = __set_access_cookies(response, token)

        return response

    _refresh_access_cookies = __refresh_access_cookies

    def __clear_access_cookies(response):
        """
        Clears the access cookies

        See: https://medium.com/lightrail/getting-token-authentication-right-in-
        a-stateless-single-page-application-57d0c6474e3

        :param response: Flask response
        :return: Flask response
        """
        response.set_cookie('access_token_sig', '', expires=0)
        response.set_cookie('access_token', '', expires=0)

        return response

    _clear_access_cookies = __clear_access_cookies

    def _authenticate(roles=None, request_type='access'):
        """
        Authenticate the user

        :param roles: list of authenticated user role IDs or a single role ID
        :param str request_type: JWT type to expect: "access" (for most
            resources) or "refresh" (for auth/refresh)

        :return: database object for the authenticated user; raises
            :class:`AuthError` on authentication error
        :rtype: afterglow_server.users.User
        """
        # If access token in HTTP Authorization header, verify and authorize.
        # otherwise, attempt to reconstruct token from cookies
        token = None
        token_hdr = request.headers.get('Authorization')
        if token_hdr:
            parts = token_hdr.split()
            if parts[0] == 'Bearer' and len(parts) == 2:
                token = parts[1]

        # for now, disable the custom header check which protects against CSRF
        # sonification requests can't have custom headers added

        # if token is None and 'X-Requested-With' in request.headers:
        if token is None:
            token_sig = request.cookies.get('access_token_sig')
            token_hdr_payload = request.cookies.get('access_token')
            if token_sig and token_hdr_payload:
                token = token_hdr_payload + '.' + token_sig

        if not token:
            raise NotAuthenticatedError()

        try:
            token_decoded = decode_jwt(token)
        except jwt.InvalidTokenError as exc:
            app.logger.info(
                'Error decoding token: %s',
                exc.message if exc.message else exc)
            raise NotAuthenticatedError()

        if token_decoded.get('type') != request_type:
            raise NotAuthenticatedError(
                error_msg='Expected {} token'.format(request_type))

        username = token_decoded.get('identity')
        if not username:
            raise NotAuthenticatedError()

        # Get the user from db
        user = User.query.filter_by(username=username).one_or_none()
        if user is None:
            raise NotAuthenticatedError()
        if not user.active:
            raise InactiveUserError()

        # Check roles if any
        if roles:
            if isinstance(roles, str) or isinstance(roles, type(u'')):
                roles = [roles]
            for role in roles:
                if not Role.query.filter_by(
                        name=role).one_or_none() in user.roles:
                    raise RoleRequiredError(role=role)

        # Make the authenticated user object available via `current_user`
        _request_ctx_stack.top.user = user

        # Make the user's auth method available via the request context stack
        method = token_decoded.get('user_claims', {}).get('method')
        if method:
            _request_ctx_stack.top.auth_method = method

        return user

    authenticate = _authenticate

    # Load auth plugins
    auth_plugins = load_plugins(
        'authentication', 'auth_plugins', AuthPlugin, app.config['USER_AUTH'])

    # Initialize security subsystem
    app.config.setdefault('SECURITY_TOKEN_MAX_AGE', None)
    app.config.setdefault('SECURITY_PASSWORD_HASH', 'sha512_crypt')
    app.config.setdefault('SECURITY_PASSWORD_SALT', 'afterglow-server')
    app.config.setdefault('SECURITY_DEFAULT_HTTP_AUTH_REALM', USER_REALM)
    app.config.setdefault('ACCESS_TOKEN_EXPIRES', timedelta(minutes=15))
    app.config.setdefault('REFRESH_TOKEN_EXPIRES', None)
    app.config.setdefault('ACCESS_TOKEN_COOKIE_EXPIRES', timedelta(days=1))

    security = Security(app, user_datastore, register_blueprint=False)

    # Register admin interface
    resource_prefix = url_prefix + 'admin/users/'

    @app.route(resource_prefix[:-1], methods=['GET', 'POST'])
    @app.route(resource_prefix + '<int:id>',
               methods=['GET', 'PUT', 'DELETE'])
    def admin_users(id=None):
        """
        List, create, update, or delete user accounts

        GET /admin/users
            - return the list of registered user IDs; non-admins get only
              their own ID

        GET /admin/users?username=...&active=...&roles=...
            - return the list of IDs of registered users matching the given
              criteria; non-admins get only their own ID

        GET /admin/users/[id]
            - return the given user info; must be admin or same user

        POST /admin/users?username=...&password=...&roles=...
            - create a new user account; must be admin; roles may include
              "admin" and "user" (separated by comma if both)

        PUT /admin/users/[id]?username=...&password=...&active=...
            - update user account; must admin or same user

        DELETE /admin/users/[id]
            - delete the given user account; must be admin

        :param int id: user ID

        :return: JSON or empty response
            GET: [{user}, {user}, ...] if `id` is missing and {user}
                otherwise, where {user} = {id: number, username: string ...}
            POST and PUT: {user}
            DELETE: empty response
        :rtype: flask.Response | str
        """
        if not app.config.get('REMOTE_ADMIN') and \
                request.remote_addr != '127.0.0.1' and (
                    request.method != 'GET' or id != 0):
            # Remote administration is not allowed, except for getting the
            # own authenticated user's info via GET /admin/users/0
            raise RemoteAdminDisabledError()

        # Any admins registered in the system?
        admin_role = Role.query.filter_by(name='admin').one()
        active_admins = admin_role.users.filter(User.active == True).count()
        if active_admins:
            # Require authentication with admin account or, for PUT and GET
            # with [id], a user account with the same ID
            user = authenticate()
            is_admin = admin_role in user.roles
            same_user = user.id == id
            if request.method in ('POST', 'DELETE') and not is_admin:
                raise AdminRequiredError()
            if id and request.method in ('GET', 'PUT') and not (
                    is_admin or same_user):
                raise AdminOrSameUserRequiredError()

        else:
            # If no admins registered yet, only allow POST for an account
            # with admin rights
            if request.method != 'POST' or \
                    'admin' not in request.args.get('roles', '').split(','):
                raise NoAdminRegisteredError()
            user = None
            is_admin = True

        # Request is authorized properly
        if request.method == 'GET':
            if id is None:
                # Return all users matching the given attributes
                q = User.query
                if user and not is_admin:
                    # For non-admin users, allow getting only their own
                    # profile
                    q = q.filter(User.id == user.id)
                if request.args.get('username'):
                    q = q.filter(User.username.ilike(
                        request.args['username'].lower()))
                if request.args.get('active'):
                    try:
                        active = bool(int(request.args['active']))
                    except ValueError:
                        raise errors.ValidationError(
                            'active', '"active" must be 0 or 1')
                    q = q.filter(User.active == active)
                if request.args.get('roles'):
                    for role in request.args['roles'].split(','):
                        q = q.filter(User.roles.any(Role.name == role))

                return json_response([u.id for u in q])

            # User ID given
            if id:
                u = User.query.get(id)
                if u is None:
                    raise UnknownUserError(id=id)
            else:
                # Special case: get the authenticated user info without
                # knowing the ID
                u = user
            return json_response(UserSchema().dump(u)[0])

        if request.method in ('POST', 'PUT'):
            username = request.args.get('username')
            password = request.args.get('password')
            active = request.args.get('active')
            if active is not None:
                try:
                    active = bool(int(active))
                except ValueError:
                    raise errors.ValidationError(
                        'active', '"active" must be 0 or 1')
                if not is_admin:
                    raise AdminRequiredError(
                        message='Must be admin to {} users'.format(
                            ('deactivate', 'activate')[active]))
            roles = request.args.get('roles')
            role_objs = []
            if roles is not None:
                if not is_admin:
                    raise AdminRequiredError(
                        message='Must be admin to set the user roles')
                for role in roles.split(','):
                    r = Role.query.filter_by(name=role).one_or_none()
                    if r is None:
                        raise errors.ValidationError(
                            'roles', 'Unknown role "{}"'.format(role))
                    role_objs.append(r)

            if request.method == 'POST':
                if not username:
                    raise errors.MissingFieldError(field='username')
                if User.query.filter(
                        db.func.lower(User.username) ==
                        username.lower()).count():
                    raise DuplicateUsernameError(username=username)
                if not password:
                    raise errors.MissingFieldError(field='password')
                if not active_admins and active is not None and not active:
                    # The first admin being added must not be inactive
                    raise CannotDeactivateTheOnlyAdminError()

                u = User()
            else:
                if id:
                    u = User.query.get(id)
                    if u is None:
                        raise UnknownUserError(id=id)
                else:
                    # Updating own account
                    id = user.id
                    u = user

                if username is not None:
                    if not username:
                        raise errors.MissingFieldError(field='username')
                    if User.query.filter(
                            db.func.lower(User.username) ==
                            username.lower(), User.id != id).count():
                        raise DuplicateUsernameError(username=username)
                if password is not None and not password:
                    raise errors.MissingFieldError(field='password')

                # At least one active admin must remain when deactivating
                # admin account or removing admin role from account
                if active_admins < 2 and admin_role in u.roles and (
                        active is not None and not active or
                        roles is not None and admin_role not in role_objs):
                    raise CannotDeactivateTheOnlyAdminError()

            try:
                if username is not None:
                    u.username = username
                if password is not None:
                    u.password = hash_password(password)
                if active is not None:
                    u.active = active
                if roles is not None or request.method == 'POST':
                    u.roles = role_objs

                if request.method == 'POST':
                    db.session.add(u)
                    db.session.flush()

                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
            else:
                return json_response(
                    UserSchema().dump(u)[0],
                    201 if request.method == 'POST' else 200)

        if request.method == 'DELETE':
            u = User.query.get(id)
            if u is None:
                raise UnknownUserError(id=id)
            if active_admins < 2 and admin_role in u.roles:
                raise CannotDeactivateTheOnlyAdminError()

            try:
                u.roles = []
                db.session.delete(u)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
            else:
                data_file_dir = os.path.join(
                    app.config['DATA_FILE_ROOT'], str(u.id))
                try:
                    shutil.rmtree(data_file_dir)
                except Exception as exc:
                    app.logger.warn(
                        'Error removing user\'s data file directory "%s" '
                        '[%s]', data_file_dir, id,
                        exc.message if exc.message else exc)
                return json_response()


# Register auth resources
@app.route(url_prefix + 'auth/methods')
@app.route(url_prefix + 'auth/methods/<id>')
def auth_plugins_view(id=None):
    """
    List Afterglow auth methods

    GET /auth/methods
        - return the list of registered authentication methods

    GET /auth/methods/[id]
        - return the given auth method info

    :return: JSON response
    :rtype: flask.Response
    """
    if id is None:
        return json_response(list(auth_plugins.values()))

    try:
        plugin = auth_plugins[id]
    except KeyError:
        try:
            plugin = auth_plugins[int(id)]
        except (KeyError, ValueError):
            raise UnknownAuthMethodError(method=id)
    return json_response(plugin)


@app.route(url_prefix + 'auth/login', methods=['GET', 'POST'])
@app.route(url_prefix + 'auth/login/<method>', methods=['GET', 'POST'])
def login(method=None):
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
    if method is None:
        # Authenticate using any of the registered methods
        methods = auth_plugins.keys()
    else:
        # Authenticate using the given method
        methods = [method]

    if not methods:
        # Auth disabled
        return json_response(dict(access_token='', refresh_token=''))

    # Try all requested auth methods
    username = None
    plugin = None
    for method in methods:
        try:
            plugin = auth_plugins[method]
        except KeyError:
            raise UnknownAuthMethodError(method=method)
        else:
            # noinspection PyBroadException,PyShadowingNames
            try:
                username = plugin.get_user()
            except HTTPException as e:
                if hasattr(e.response, 'status_code') and \
                        e.response.status_code == 302:
                    # Allow redirects from multi-stage auth plugins like
                    # OAuth
                    raise
            except Exception:
                # Auth failed, try other methods
                pass
            else:
                # Auth succeeded
                break
    if username is None:
        raise NotAuthenticatedError()

    # Get the user from db
    need_commit = False
    user = User.query.filter_by(username=username).one_or_none()
    if user is None:
        # Authenticated but not in the db; register a new Afterglow user if
        # allowed by plugin or the global config option
        register_users = plugin.register_users
        if register_users is None:
            register_users = app.config.get(
                'REGISTER_AUTHENTICATED_USERS', True)
        if not register_users:
            raise NotAuthenticatedError(
                error_msg='Automatic user registration disabled')

        user = User()
        user.username = username
        user.password = ''
        user.roles = [Role.query.filter_by(name='user').one()]
        db.session.add(user)
        need_commit = True

    if not user.auth_methods:
        # This is the first user's login; allow the current auth method
        user.auth_methods = method
        need_commit = True
    elif method not in user.auth_methods.split(','):
        # Deny login via any new method until explicitly allowed by POSTing to
        # auth/user/auth_methods
        raise NotAuthenticatedError(
            error_msg='Authentication method not allowed')

    if need_commit:
        db.session.commit()

    if not user.active:
        raise InactiveUserError()

    # Return access and refresh tokens
    access_token = _create_token(
        user.username, app.config.get('ACCESS_TOKEN_COOKIE_EXPIRES'),
        dict(method=method))
    # return _set_access_cookies(json_response(), access_token)
    return _set_access_cookies(json_response(dict(
        access_token=access_token,
        refresh_token=_create_token(
            user.username, app.config.get('REFRESH_TOKEN_EXPIRES'),
            dict(method=method), 'refresh'),
    )), access_token)


@app.route(url_prefix + 'auth/logout', methods=['GET', 'POST'])
@auth_required
def logout():
    """
    Logout from Afterglow

    GET|POST /auth/logout
        - log the current user out

    :return: empty JSON response
    :rtype: flask.Response
    """
    for plugin in auth_plugins.values():
        # noinspection PyBroadException
        try:
            plugin.logout()
        except Exception:
            pass

    return _clear_access_cookies(json_response())


# @app.route(url_prefix + 'auth/refresh', methods=['POST'])
# @auth_required(request_type='refresh')
# def refresh():
#     """
#     Refresh access token
#
#     POST /auth/refresh
#         - refresh the expired access token; auth headers must contain a valid
#           refresh token
#
#     :return: JSON {"access_token": "token", "refresh_token": token}
#     :rtype: flask.Response
#     """
#     if not auth_plugins:
#         # Auth disabled
#         return json_response(dict(access_token='', refresh_token=''))
#
#     # Install the user claims loader to add the actual auth method to JWT; the
#     # method is extracted from refresh token
#     # noinspection PyProtectedMember
#     from flask import _request_ctx_stack
#     try:
#         method = _request_ctx_stack.top.auth_method
#     except Exception:
#         raise NotAuthenticatedError(
#             error_msg='Refresh token does not contain auth method')
#
#     return _refresh_access_cookies(json_response(dict(
#         access_token=_create_token(
#             current_user.username, app.config.get('ACCESS_TOKEN_EXPIRES'),
#             dict(method=method)),
#         refresh_token=_create_token(
#             current_user.username, app.config.get('REFRESH_TOKEN_EXPIRES'),
#             dict(method=method), 'refresh'),
#     )))


@app.route(url_prefix + 'auth/user')
@auth_required
def auth_user():
    """
    Get the currently logged in user info

    :return: currently logged in user info; if auth is disabled, returns empty
        structure; if the user is not logged in, returns HTTP 401
    :rtype: flask.Response
    """
    return json_response(UserSchema().dump(current_user)[0])


@app.route(url_prefix + 'auth/user/auth_methods', methods=['POST'])
@auth_required
def auth_user_auth_methods():
    """
    Allow the user to authenticate using the given method

    POST auth/user/auth_methods
    method=[method ID]

    :return: empty response
    :rtype: flask.Response
    """
    user = User.query.filter_by(username=current_user.username).one_or_none()
    if user is None:
        raise NotAuthenticatedError(error_msg='User never logged in')
    method = request.args.get('method')
    if method not in auth_plugins:
        raise errors.ValidationError(
            'method', 'Unknown auth method "{}"'.format(method))
    user.auth_methods = ','.join(set(user.auth_methods.split(',') + [method]))
    db.session.commit()
    return json_response()
