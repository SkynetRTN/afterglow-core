"""
Afterglow Core: user routes
"""
import secrets

# noinspection PyProtectedMember
from flask import (
    request, render_template, redirect, url_for, _request_ctx_stack)
from flask_security.utils import hash_password, verify_password
import marshmallow

from .. import app, json_response
from ..auth import (
    auth_required, clear_access_cookies, oauth_plugins,
    set_access_cookies)
from ..oauth2 import OAuth2Token, mem_db
from ..users import User, Role, db
from ..models.user import UserSchema
from ..models.oauth2 import OAuth2TokenSchema
from ..errors import MissingFieldError, ValidationError
from ..errors.oauth2 import UnknownTokenError
from ..errors.auth import (
    HttpAuthFailedError, InitPageNotAvailableError,
    LocalAccessRequiredError, NotInitializedError)


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
    request.user = user

    return set_access_cookies(json_response())


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


@app.route('/users/tokens', methods=['GET', 'POST'])
@auth_required
def tokens():
    """
    Return personal access tokens

    :return: JSON object {"items": list of tokens}
    :rtype: flask.Response
    """

    if request.method == 'GET':
        tokens = mem_db.query(OAuth2Token).filter_by(type="personal", user_id=request.user.id, revoked=False).all()

        res = OAuth2TokenSchema(only=("id", "note")).dump(tokens, many=True)
        return json_response({
            'items': res
        })

    if request.method == 'POST':
        note = request.args.get('note')
        if not note or note == '':
            raise ValidationError('note', 'Note cannot be empty')

        access_token = secrets.token_hex(20)

        token = OAuth2Token(
            token_type='personal',
            access_token=access_token,
            user_id=request.user.id,
            note=note
        )
        mem_db.session.add(token)
        mem_db.session.commit()
        res = OAuth2TokenSchema().dump(token)
        if marshmallow.__version_info__ < (3, 0):
            res = res[0]
        return json_response(res, 201)

@app.route('/users/tokens/<int:token_id>', methods=['DELETE'])
@auth_required
def token(token_id: int = None):
    if request.method == 'DELETE':
        token = mem_db.query(OAuth2Token).filter_by(type="personal", user_id=request.user.id, id=token_id).one_or_none()

        if not token:
            raise UnknownTokenError()

        mem_db.delete(token)
        mem_db.commit()

        return json_response()
        