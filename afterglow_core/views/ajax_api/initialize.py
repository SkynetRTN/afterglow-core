
import json

from flask import Response, request, render_template, redirect, url_for
from flask_security.utils import hash_password, verify_password

from ... import app, json_response
from ...auth import (
    auth_required, clear_access_cookies, oauth_plugins, authenticate,
    set_access_cookies)
from ...resources.users import DbUser, DbRole, DbIdentity, db
from ...schemas.api.v1 import UserSchema
from ...errors import ValidationError, MissingFieldError
from ...errors.auth import (
    HttpAuthFailedError, NotInitializedError, UnknownAuthMethodError,
    NotAuthenticatedError, InitPageNotAvailableError)

from . import url_prefix


@app.route(url_prefix + 'initialize', methods=['POST'])
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
    if DbUser.query.count() != 0:
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
            u = DbUser(
                username=username,
                password=hash_password(password),
                email=request.args.get('email'),
                first_name=request.args.get('first_name'),
                last_name=request.args.get('last_name'),
                birth_date=request.args.get('birth_date'),
                active=True,
                roles=[
                    DbRole.query.filter_by(name='admin').one(),
                    DbRole.query.filter_by(name='user').one(),
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
