"""
Afterglow Core: top-level and initialization routes
"""

# noinspection PyProtectedMember
from flask import (
    request, render_template, redirect, url_for, _request_ctx_stack)
from flask_security.utils import hash_password, verify_password
import marshmallow

from .. import app, json_response
from ..auth import (
    auth_required, clear_access_cookies, create_token, oauth_plugins,
    set_access_cookies)
from ..users import User, Role, db
from ..models.user import UserSchema
from ..errors import MissingFieldError, ValidationError
from ..errors.auth import (
    HttpAuthFailedError, InitPageNotAvailableError,
    LocalAccessRequiredError, NotInitializedError)


__all__ = []


@app.route('/', methods=['GET'])
@auth_required(allow_redirect=True)
def default():
    """
    Homepage for Afterglow Core

    GET /
        - Homepage/Dashboard

    :return: Afterglow Core homepage
    :rtype: flask.Response
    """
    return render_template('index.html.j2', current_user=request.user)


@app.route('/initialize', methods=['GET', 'POST'])
def initialize():
    """
    Homepage for Afterglow Core

    GET|POST /initialize
        - Homepage/Initialize

    :return: Afterglow Core initialization
    :rtype: flask.Response
    """
    if User.query.count() != 0:
        raise InitPageNotAvailableError()

    if not app.config.get('REMOTE_ADMIN') and \
            request.remote_addr != '127.0.0.1':
        # Remote administration is not allowed
        raise LocalAccessRequiredError()

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

        email = request.args.get('email')
        if not email:
            raise MissingFieldError('email')

        admin_role = Role.query.filter_by(name='admin').one()
        user_role = Role.query.filter_by(name='user').one()
        roles = [admin_role, user_role]

        try:
            u = User()
            u.username = username
            u.password = hash_password(password)
            u.email = email
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


@app.route('/login', methods=['GET', 'POST'])
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


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """
    Logout from Afterglow

    GET|POST /auth/logout
        - log the current user out

    :return: empty JSON response
    :rtype: flask.Response
    """
    return clear_access_cookies(redirect(url_for('login')))


@app.route('/token', methods=['GET', 'POST'])
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
