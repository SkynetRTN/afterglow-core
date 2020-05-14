"""
Afterglow Core: user routes
"""
import secrets

from flask import request, render_template, redirect, url_for
from flask_security.utils import verify_password

from .. import app, json_response
from ..auth import (
    auth_required, clear_access_cookies, oauth_plugins,
    set_access_cookies)
from ..users import User, PersistentToken, db
from ..models.user import TokenSchema
from ..errors import ValidationError
from ..errors.auth import (
    HttpAuthFailedError, NotInitializedError, UnknownTokenError)


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
@app.route('/users/tokens/<int:token_id>', methods=['DELETE'])
@auth_required
def tokens(token_id: int = None):
    """
    Return, create, or delete personal access tokens

    :return:
        GET /users/tokens: JSON object {"items": list of tokens}
        POST /users/tokens: {token}
        DELETE /users/tokens/[token id]: empty response
    :rtype: flask.Response
    """
    if request.method == 'GET':
        personal_tokens = PersistentToken.query.filter_by(
            token_type='personal', user_id=request.user.id, revoked=False).all()

        res = TokenSchema(only=('id', 'note')).dump(personal_tokens, many=True)

        return json_response({
            'items': res
        })

    if request.method == 'POST':
        note = request.args.get('note')
        if not note or note == '':
            raise ValidationError('note', 'Note cannot be empty')

        access_token = secrets.token_hex(20)

        personal_token = PersistentToken(
            access_token=access_token,
            user_id=request.user.id,
            note=note,
        )
        try:
            db.session.add(personal_token)
            db.session.commit()
        except Exception:
            # noinspection PyBroadException
            try:
                db.session.rollback()
            except Exception:
                pass
            raise

        return json_response(TokenSchema().dump(personal_token), 201)

    if request.method == 'DELETE':
        personal_token = PersistentToken.query\
            .filter_by(
                token_type='personal',
                user_id=request.user.id,
                id=token_id)\
            .one_or_none()

        if not personal_token:
            raise UnknownTokenError()

        try:
            db.session.delete(personal_token)
            db.session.commit()
        except Exception:
            # noinspection PyBroadException
            try:
                db.session.rollback()
            except Exception:
                pass
            raise

        return json_response()
