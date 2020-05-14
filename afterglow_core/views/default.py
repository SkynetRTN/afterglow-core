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
    auth_required, clear_access_cookies, oauth_plugins,
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


