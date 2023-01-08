
from flask import Response, request
from flask_security.utils import hash_password

from ... import json_response
from ...resources import users
from ...schemas.api.v1 import UserSchema
from ...errors import MissingFieldError
from ...errors.auth import InitPageNotAvailableError
from . import ajax_blp as blp


@blp.route('/initialize', methods=['POST'])
def initialize() -> Response:
    """
    Afterglow Core initialization

    GET /initialize
        - render initialization page

    POST /initialize
        - create admin user

    :return::
        GET: initialization page HTML
        POST: JSON-serialized :class:`UserSchema`
    """
    if users.DbUser.query.count() != 0:
        raise InitPageNotAvailableError()

    if request.method == 'POST':
        username = request.args.get('username')
        if not username:
            raise MissingFieldError('username')

        password = request.args.get('password')
        if not password:
            raise MissingFieldError('password')
        # TODO check security of password

        try:
            u = users.DbUser(
                username=username,
                password=hash_password(password),
                email=request.args.get('email'),
                first_name=request.args.get('first_name'),
                last_name=request.args.get('last_name'),
                active=True,
                roles=[
                    users.DbRole.query.filter_by(name='admin').one(),
                    users.DbRole.query.filter_by(name='user').one(),
                ],
                settings=request.args.get('settings'),
            )
            users.db.session.add(u)
            users.db.session.commit()
        except Exception:
            users.db.session.rollback()
            raise
        else:
            return json_response(UserSchema().dump(u), 201)
