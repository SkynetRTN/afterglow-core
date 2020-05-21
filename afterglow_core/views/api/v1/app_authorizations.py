"""
Afterglow Core: login and user account management routes
"""

import os
import shutil
import json

from flask_security.utils import hash_password
from flask import request

from . import url_prefix
from .... import app, json_response
from ....auth import auth_required
from ....oauth2 import oauth_clients
from ....users import Role, User, UserClient, db
from ....models.user import UserSchema
from ....errors import MissingFieldError, ValidationError
from ....errors.auth import (
    AdminRequiredError, UnknownUserError, CannotDeactivateTheOnlyAdminError,
    DuplicateUsernameError, CannotDeleteCurrentUserError,
    LocalAccessRequiredError)
from ....errors.oauth2 import UnknownClientError, MissingClientIdError

@app.route(url_prefix + 'app-authorizations',
           methods=['GET', 'POST'])
@app.route(url_prefix +
           'app-authorizations/<int:id>',
           methods=['DELETE'])
@auth_required
def app_authorizations(id: int = None):
    user_id = request.user.id

    if request.method == 'GET':
        user_clients = UserClient.query.filter_by(user_id=user_id).all()
        result = []
        for user_client in user_clients:
            client = oauth_clients[user_client.client_id]
            result.append(dict(
                id=user_client.id,
                client_id=user_client.client_id,
                user_id=user_client.user_id,
                client=dict(
                    client_id=client.client_id,
                    name=client.name
                )
            ))
        return json.dumps({'items': result})

    if request.method == 'POST':
        try:
            client_id = request.args['client_id']
        except KeyError:
            raise MissingClientIdError()

        if client_id not in oauth_clients:
            raise UnknownClientError(id=client_id)

        user_client = UserClient.query.filter_by(
            user_id=user_id, client_id=client_id).one_or_none()

        if not user_client:
            try:
                db.session.add(UserClient(
                    user_id=user_id, client_id=client_id))
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
            return json_response('', 201)

        return json_response()

    if request.method == 'DELETE':
        # TODO remove all active tokens associated with user/client
        try:
            uc = UserClient.query.filter_by(
                user_id=user_id, id=id).delete()

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return json_response({})
