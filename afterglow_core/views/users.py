from __future__ import absolute_import, division, print_function

import marshmallow
import json
from flask_security.utils import hash_password, verify_password
from flask import redirect, request, render_template, url_for

from ..auth import auth_required, authenticate, create_token, AdminRequiredError, \
    UnknownUserError, CannotDeactivateTheOnlyAdminError, CannotDeleteCurrentUserError,  \
    _clear_access_cookies, _set_access_cookies, oauth_plugins, NotInitializedError, security, \
    HttpAuthFailedError, CannotDeactivateTheOnlyAdminError, DuplicateUsernameError
from ..oauth2 import MissingClientIdError, UnknownClientError, oauth_clients
from ..users import Role, User, UserSchema, UserClient, AnonymousUserRole, AnonymousUser, db
from .. import app, errors, json_response, url_prefix

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
    #TODO Ensure CORS is disabled for POSTS to this endpoint

    #Do not allow login if Afterglow Core has not yet been configured
    if User.query.count() == 0:
        if request.remote_addr == '127.0.0.1':
            return redirect(url_for('initialize'))
        
        raise NotInitializedError()

    
    
    next_url = request.args.get('next')
    if not next_url: next_url = '/'

    if request.method == 'GET':
        return render_template('users/login.html.j2', oauth_plugins=oauth_plugins.values(), next_url=next_url)

    username = request.args.get('username')
    if not username:
        raise errors.ValidationError(
            'username', 'Username cannot be empty')
        
    password = request.args.get('password')
    if not password:
        raise errors.ValidationError(
            'password', 'Password cannot be empty')

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
    
    return _set_access_cookies(json_response(dict()), access_token)

@app.route('/users/logout', methods=['GET', 'POST'])
def logout():
    """
    Logout from Afterglow

    GET|POST /auth/logout
        - log the current user out

    :return: empty JSON response
    :rtype: flask.Response
    """

    return _clear_access_cookies(redirect(url_for('login')))

# Register OAuth2.0 authorization code redirect handler
@app.route('/users/oauth2/<string:plugin_id>')
def oauth2_authorized(plugin_id):
    """
    OAuth2.0 authorization code granted redirect endpoint

    :return: redirect to original request URL
    :rtype: flask.Response
    """

    #Do not allow login if Afterglow Core has not yet been configured
    if User.query.count() == 0:
        raise NotInitializedError()

    state = request.args.get('state')
    if not state:
        #TODO:  render error page
        raise Exception("missing state parameter")
    
    try:
        state = json.loads(state)
    except json.JSONDecodeError:
        #TODO:  render error page
        raise Exception("invalid state parameter")

    if not plugin_id or plugin_id not in oauth_plugins.keys():
        #TODO:  render error page
        raise Exception("page not found")

    oauth_plugin = oauth_plugins[plugin_id]

    if not request.args.get('code'):
        #TODO:  render error page
        raise Exception("invalid code")

    token = oauth_plugin.get_token(request.args.get('code'))
    user_profile = oauth_plugin.get_user_profile(token)

    if not user_profile:
        raise NotAuthenticatedError()

    

    # Get the user from db
    method_uid = "{}:{}".format(oauth_plugin.name, user_profile.id)
    user = User.query.filter(User.auth_methods.like("%{}%".format(method_uid))).one_or_none()
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
        user.username =  None
        user.password = None
        user.alias = user_profile.username if user_profile.first_name else None
        user.first_name = user_profile.first_name if user_profile.first_name else None
        user.last_name = user_profile.last_name if user_profile.last_name else None
        user.email = user_profile.email if user_profile.email else None
        user.auth_methods = method_uid
        user.roles = [Role.query.filter_by(name='user').one()]
        db.session.add(user)
        db.session.commit()

    next_url = state.get('next')
    if not next_url: next_url = '/'
    expires_delta = app.config.get('ACCESS_TOKEN_EXPIRES')
    access_token = create_token(
        user.id, expires_delta, dict(method=oauth_plugin.name))
    return _set_access_cookies(redirect(next_url), access_token)

# noinspection PyUnusedLocal
@app.route('/users/oauth2/consent', methods=['GET', 'POST'])
@auth_required('user', allow_redirect=True)
def oauth2_consent():
    client_id = request.args.get('client_id')
    if not client_id:
        #TODO Return JSON error for XHR or render error page for GET
        raise errors.MissingFieldError('client_id')

    if client_id not in oauth_clients:
        #TODO Return JSON error for XHR or render error page for GET
        raise Exception('invalid oauth client id')

    client = oauth_clients[client_id]

    if request.method == 'GET':
        return render_template('users/consent.html.j2', oauth_client=client, next_url=request.args.get('next'))

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


##################################
####            API         ######
##################################

def parse_user_fields():
    username = request.args.get('username')
    if username is not None:
        if not username:
            raise errors.ValidationError(
                'username', 'Username cannot be empty')

    password = request.args.get('password')

    if password is not None and not password:
        raise errors.ValidationError(
            'password', 'Password cannot be empty')

    active = request.args.get('active')
    if active is not None:
        try:
            active = bool(int(active))
        except ValueError:
            raise errors.ValidationError(
                'active', '"active" must be 0 or 1')

    roles = request.args.get('roles')
    if roles is not None:
        role_objs = []
        for role in roles.split(','):
            r = Role.query.filter_by(name=role).one_or_none()
            if r is None:
                raise errors.ValidationError(
                    'roles', 'Unknown role "{}"'.format(role))
            role_objs.append(r)
        roles = roles_objs

    return (username, password, active, roles)

@app.route(url_prefix + 'users', methods=['GET', 'POST'])
@auth_required('user')
def users():
    """
    List, create user accounts

    GET /users
        - return the list of registered user IDs; non-admins get only
            their own ID

    GET /users?username=...&active=...&roles=...
        - return the list of IDs of registered users matching the given
            criteria; non-admins get only their own ID

    POST /users?username=...&password=...&roles=...
        - create a new user account; must be admin; roles may include
            "admin" and "user" (separated by comma if both)

    :return: JSON or empty response
        GET: [{user}, {user}, ...]
        POST: {user}
        DELETE: empty response
    :rtype: flask.Response | str
    """
    admin_role = Role.query.filter_by(name='admin').one()
    is_admin = admin_role in request.user.roles
    if not is_admin:
        raise AdminRequiredError()

    if not app.config.get('REMOTE_ADMIN') and \
            request.remote_addr != '127.0.0.1' and (
                request.method != 'GET'):
        # Remote administration is not allowed
        raise AdminRequiredError()

    # Request is authorized properly
    if request.method == 'GET':
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
            
    if request.method == 'POST':
        (username, password, active, roles) = parse_user_fields()
        if username is None:
            raise errors.ValidationError(
                'username', 'Username is required')
        if password is None:
            raise errors.ValidationError(
                'password', 'Password is required')
        if active is not None and not active:
            raise errors.ValidationError(
                'active', 'Cannot create inactive account')
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
            res = UserSchema().dump(u)
            if marshmallow.__version_info__ < (3, 0):
                res = res[0]
            return json_response(res, 201)


@app.route(url_prefix + 'users/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@auth_required('user')
def user(id):
    """
    View, update, or delete a user account

    GET /users/[id]
        - return the given user info; must be admin or same user

    PUT /users/[id]?username=...&password=...&active=...
        - update user account; must be admin or same user

    DELETE /users/[id]
        - delete the given user account; must be admin

    :param int id: user ID

    :return: JSON or empty response
        GET:  {id: number, username: string ...}
        POST and PUT: {user}
        DELETE: empty response
    :rtype: flask.Response | str
    """
    admin_role = Role.query.filter_by(name='admin').one()
    admin_required = request.user.id != id
    is_admin = admin_role in request.user.roles

    if admin_required and not is_admin:
        raise AdminRequiredError()

    if admin_required and not app.config.get('REMOTE_ADMIN') and \
            request.remote_addr != '127.0.0.1' and (
                request.method != 'GET'):
        # Remote administration is not allowed
        raise AdminRequiredError()

    # Request is authorized properly

    u = User.query.get(id)
    if u is None:
        raise UnknownUserError(id=id)
    
    if request.method == 'GET':
        res = UserSchema().dump(u)
        if marshmallow.__version_info__ < (3, 0):
            res = res[0]
        return json_response(res)

    # At least one active admin must remain when deactivating
    # admin account or removing admin role from account
    active_admins = admin_role.users.filter(User.active == True).count()
    
    
    if request.method == 'PUT':
        (username, password, active, roles) = parse_user_fields()

        if username is not None and User.query.filter(
                db.func.lower(User.username) ==
                username.lower(), User.id != id).count():
            raise DuplicateUsernameError(username=username)

        if active is not None:
            if not is_admin:
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
            res = UserSchema().dump(u)
            if marshmallow.__version_info__ < (3, 0):
                res = res[0]
            return json_response(
                res, 200)

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
                    '[%s]', data_file_dir, id, exc)
            return json_response()


@app.route(url_prefix + 'users/<int:user_id>/authorized-apps', methods=['GET', 'POST'])
@auth_required('user')
def users_authorized_apps(user_id):
    admin_role = Role.query.filter_by(name='admin').one()
    admin_required = request.user.id != user_id
    is_admin = admin_role in request.user.roles

    if admin_required and not is_admin:
        raise AdminRequiredError()

    if request.method == 'GET':
        authorized_client_ids = [c.client_id for c in UserClient.query.filter_by(
                user_id=user_id)]
        clients = [dict(id=c.client_id, name=c.name) for c in oauth_clients.values() if c.client_id in authorized_client_ids]
        
        return json.dumps(clients)
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
        

@app.route(url_prefix + 'users/<int:user_id>/authorized-apps/<string:client_id>', methods=['DELETE'])
@auth_required('user')
def users_authorized_app(user_id, client_id):
    #TODO remove all active tokens associated with user/client
    admin_role = Role.query.filter_by(name='admin').one()
    admin_required = request.user.id != user_id
    is_admin = admin_role in request.user.roles

    if admin_required and not is_admin:
        raise AdminRequiredError()

    if client_id not in oauth_clients:
        raise UnknownClientError(id=client_id)

    print("deleting", user_id, client_id)
    UserClient.query.filter_by(
        user_id=user_id, client_id=client_id).delete()
    db.session.commit()
    return json_response({})
        

#aliases for logged in user 
@app.route(url_prefix + 'user', methods=['GET', 'PUT'])
@auth_required
def current_user():
    return user(request.user.id)

@app.route(url_prefix + 'user/authorized-apps', methods=['GET', 'POST'])
@auth_required('user')
def current_user_authorized_apps():
    return users_authorized_apps(request.user.id)

@app.route(url_prefix + 'user/authorized-apps/<string:client_id>', methods=['DELETE'])
@auth_required('user')
def current_user_authorized_app(client_id):
    return users_authorized_app(request.user.id, client_id)