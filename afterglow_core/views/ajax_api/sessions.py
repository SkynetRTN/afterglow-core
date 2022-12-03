
from flask import g, request, session
from flask_security.utils import verify_password

from ... import json_response
from ...auth import auth_required, set_access_cookies, clear_access_cookies
from ...resources.users import DbUser
from ...errors import ValidationError
from ...errors.auth import HttpAuthFailedError
from . import ajax_blp as blp


# @csrf.exempt
@blp.route('/sessions', methods=['POST'])
def sessions_post():
    # Login using local identity
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

    # Set token cookies
    g._login_user = request.user = user

    return set_access_cookies(json_response(), user.id)


@blp.route('/sessions', methods=['DELETE'])
@auth_required
def sessions_delete():
    session.clear()
    return clear_access_cookies(json_response())
