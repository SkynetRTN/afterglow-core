from __future__ import absolute_import, division, print_function

from flask import redirect, request, render_template
from flask_security.utils import hash_password
import marshmallow

from ..auth import auth_required, authenticate, create_token, LocalAccessRequiredError, InitPageNotAvailableError
from ..users import User, UserSchema, Role, db
from .. import app, errors, json_response, url_prefix

__all__ = [
    'default',
]

@app.route('/', methods=['GET'])
@auth_required('user', allow_redirect=True)
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

    GET /
        - Homepage/Initialize

    :return: Afterglow Core initialization
    :rtype: flask.Response
    """
    if User.query.count() != 0:
        raise InitPageNotAvailableError()

    if request.remote_addr != '127.0.0.1':
        # Remote administration is not allowed
        raise LocalAccessRequiredError()

    if request.method == 'GET':
        return render_template('initialize.html.j2')

    if request.method == 'POST':
        username = request.args.get('username')
        if not username:
            raise errors.ValidationError(
                'username', 'Username cannot be empty')
            
        password = request.args.get('password')
        if not password:
            raise errors.ValidationError(
                'password', 'Password cannot be empty')
        #TODO check security of password

        email = request.args.get('email')
        if not email:
            raise errors.ValidationError(
                'email', 'Email cannot be empty')

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
