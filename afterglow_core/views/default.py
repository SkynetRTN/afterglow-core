"""
Afterglow Core: top-level and initialization routes
"""

from flask import request, render_template
from flask_security.utils import hash_password

from .. import app, json_response
from ..auth import auth_required
from ..users import User, Role, db
from ..models.user import UserSchema
from ..errors import MissingFieldError
from ..errors.auth import InitPageNotAvailableError, LocalAccessRequiredError


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

        try:
            u = User(
                username=username,
                password=hash_password(password),
                email=email,
                first_name=request.args.get('first_name'),
                last_name=request.args.get('last_name'),
                birth_date=request.args.get('birth_date'),
                active=True,
                roles=[
                    Role.query.filter_by(name='admin').one(),
                    Role.query.filter_by(name='user').one(),
                ],
                settings=request.args.get('settings'),
            )
            db.session.add(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            return json_response(UserSchema().dump(u), 201)
