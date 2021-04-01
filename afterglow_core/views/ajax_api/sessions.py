import hashlib
import secrets
import time
from flask import make_response, abort, request, current_app, redirect, Response, session
from flask_security.utils import hash_password, verify_password

from ... import app, json_response
from ...auth import auth_required, set_access_cookies, clear_access_cookies
from ...resources.users import DbPersistentToken, DbUser, db
from ...schemas import Resource
from ...errors import ValidationError
from ...errors.auth import HttpAuthFailedError
from . import url_prefix

# @csrf.exempt
@app.route(url_prefix + 'sessions', methods=['POST'])
def post():
    #login using local identity
    redirect_uri = request.json.get('redirect', '/')

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
    
@app.route(url_prefix + 'sessions', methods=['DELETE'])
@auth_required
def delete():
    session.clear()
    return clear_access_cookies(json_response())