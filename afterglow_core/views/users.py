"""
Afterglow Core: login and user account management routes
"""

import os
import shutil
import json

from flask_security.utils import hash_password, verify_password
from flask import redirect, request, render_template, url_for

from .. import app, json_response, url_prefix
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
        raise NotAuthenticatedError()

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
        user.alias = user_profile.username if user_profile.first_name else None
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


# ############################## #
# ###            API         ### #
# ############################## #

def parse_user_fields():
    username = request.args.get('username')
    if username is not None:
        if not username:
            raise ValidationError('username', 'Username cannot be empty')

    password = request.args.get('password')

    if password is not None and not password:
        raise ValidationError('password', 'Password cannot be empty')

    active = request.args.get('active')
    if active is not None:
        try:
            active = bool(int(active))
        except ValueError:
            raise ValidationError('active', '"active" must be 0 or 1')

    roles = request.args.get('roles')
    if roles is not None:
        role_objs = []
        for role in roles.split(','):
            r = Role.query.filter_by(name=role).one_or_none()
            if r is None:
                raise ValidationError('roles', 'Unknown role "{}"'.format(role))
            role_objs.append(r)
        roles = role_objs

    return username, password, active, roles


@app.route(url_prefix + 'users', methods=['GET', 'POST'])
@app.route(url_prefix + 'users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@auth_required
def users(user_id: int = None):
    """
    List, create, and update user accounts

    GET /users
        - return the list of registered user IDs; non-admins get only
            their own ID

    GET /users?username=...&active=...&roles=...
        - return the list of IDs of registered users matching the given
            criteria; non-admins get only their own ID

    POST /users?username=...&password=...&roles=...
        - create a new user account; must be admin; roles may include
            "admin" and "user" (separated by comma if both)

    GET /users/[id]
        - return the given user info; must be admin or same user

    PUT /users/[id]?username=...&password=...&active=...
        - update user account; must be admin or same user

    DELETE /users/[id]
        - delete the given user account; must be admin

    :params user_id: ID of the user to retrieve/update/delete

    :return: JSON or empty response
        GET: {"items"; [{user}, {user}, ...]}
        POST: {user}
        DELETE: empty response
    :rtype: flask.Response | str
    """
    # Admin rights are required for listing, creating, and deleting users;
    # not required for retrieving and updating the current user's profile
    if request.method not in ('GET', 'PUT') or user_id != request.user.id:
        if not request.user.is_admin:
            raise AdminRequiredError()
        if not app.config.get('REMOTE_ADMIN') and \
                request.remote_addr != '127.0.0.1':
            raise LocalAccessRequiredError()

    # Request is authorized properly
    if request.method == 'GET' and user_id is None:
        # Return all users matching the given attributes
        q = User.query
        if request.args.get('username'):
            q = q.filter(User.username.ilike(
                request.args['username'].lower()))
        if request.args.get('active'):
            try:
                active = bool(int(request.args['active']))
            except ValueError:
                raise ValidationError('active', '"active" must be 0 or 1')
            q = q.filter(User.active == active)
        if request.args.get('roles'):
            for role in request.args['roles'].split(','):
                q = q.filter(User.roles.any(Role.name == role))

        return json_response({'items': UserSchema().dump(q.all(), many=True)})

    if request.method == 'POST':
        username, password, active, roles = parse_user_fields()
        if username is None:
            raise MissingFieldError('username')
        if password is None:
            raise MissingFieldError('password')
        if active is not None and not active:
            raise ValidationError('active', 'Cannot create inactive account')
        if roles is None:
            roles = []

        try:
            u = User()
            u.username = username
            u.password = hash_password(password)
            u.active = True
            u.roles = roles

            db.session.add(u)
            db.session.flush()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            return json_response(UserSchema().dump(u), 201)

    # A /users/[id] request
    u = User.query.get(user_id)
    if u is None:
        raise UnknownUserError(id=user_id)

    if request.method == 'GET':
        return json_response(UserSchema().dump(u))

    # At least one active admin must remain when deactivating
    # admin account or removing admin role from account
    admin_role = Role.query.filter_by(name='admin').one()
    active_admins = admin_role.users.filter(User.active == True).count()

    if request.method == 'PUT':
        username, password, active, roles = parse_user_fields()

        if username is not None and User.query.filter(
                db.func.lower(User.username) ==
                username.lower(), User.id != user_id).count():
            raise DuplicateUsernameError(username=username)

        if active is not None:
            if not request.user.is_admin:
                raise AdminRequiredError(
                    message='Must be admin to {} users'.format(
                        ('deactivate', 'activate')[active]))

            if active_admins < 2 and admin_role in u.roles and (
                    active is not None and not active or
                    roles is not None and admin_role not in roles):
                raise CannotDeactivateTheOnlyAdminError()

        try:
            if username is not None:
                u.username = username
            if password is not None:
                u.password = hash_password(password)
            if active is not None:
                u.active = active
            if roles is not None:
                u.roles = roles

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            return json_response(UserSchema().dump(u), 200)

    if request.method == 'DELETE':
        if u.id == request.user.id:
            raise CannotDeleteCurrentUserError()

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
                    '[%s]', data_file_dir, user_id, exc)
            return json_response()


@app.route(url_prefix + 'users/<int:user_id>/authorized-apps',
           methods=['GET', 'POST'])
@app.route(url_prefix +
           'users/<int:user_id>/authorized-apps/<str:client_id>',
           methods=['DELETE'])
@auth_required
def users_authorized_apps(user_id: int, client_id: str = None):
    if request.user.id != user_id:
        if not request.user.is_admin:
            raise AdminRequiredError()
        if not app.config.get('REMOTE_ADMIN') and \
                request.remote_addr != '127.0.0.1':
            raise LocalAccessRequiredError()

    if request.method == 'GET':
        authorized_client_ids = [
            c.client_id for c in UserClient.query.filter_by(user_id=user_id)]
        clients = [dict(id=c.client_id, name=c.name)
                   for c in oauth_clients.values()
                   if c.client_id in authorized_client_ids]

        return json.dumps({'items': clients})

    if request.method == 'POST':
        try:
            client_id = request.args['client_id']
        except KeyError:
            raise MissingClientIdError()

        if client_id not in oauth_clients:
            raise UnknownClientError(id=client_id)

        user_client = UserClient.query.filter_by(
            user_id=user_id, client_id=client_id).one_or_none()

        if not user_client:
            try:
                db.session.add(UserClient(
                    user_id=user_id, client_id=client_id))
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
            return json_response('', 201)

        return json_response()

    if request.method == 'DELETE':
        # TODO remove all active tokens associated with user/client
        if client_id not in oauth_clients:
            raise UnknownClientError(id=client_id)

        try:
            UserClient.query.filter_by(
                user_id=user_id, client_id=client_id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return json_response({})


# Aliases for logged in user
@app.route(url_prefix + 'user', methods=['GET', 'PUT'])
def current_user():
    return users(request.user.id)


@app.route(url_prefix + 'user/authorized-apps', methods=['GET', 'POST'])
@app.route(url_prefix + 'user/authorized-apps/<str:client_id>',
           methods=['DELETE'])
def current_user_authorized_apps(client_id: str = None):
    return users_authorized_apps(request.user.id, client_id)
