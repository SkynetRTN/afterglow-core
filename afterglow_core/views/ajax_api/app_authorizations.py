"""
Afterglow Core: login and user account management routes
"""

from flask import Response, current_app, request

from ... import json_response
from ...auth import auth_required
from ...oauth2 import oauth_clients
from ...resources.users import DbUserClient
from ...errors.oauth2 import UnknownClientError, MissingClientIdError
from . import ajax_blp as blp


@blp.route('/app-authorizations', methods=['GET', 'POST'])
@blp.route('/app-authorizations/<int:id>', methods=['DELETE'])
@auth_required
def app_authorizations(id: int = None) -> Response:
    user_id = request.user.id

    if request.method == 'GET':
        user_clients = DbUserClient.query.filter_by(user_id=user_id).all()
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
        return json_response(result)

    if request.method == 'POST':
        try:
            client_id = request.args['client_id']
        except KeyError:
            raise MissingClientIdError()

        if client_id not in oauth_clients:
            raise UnknownClientError(id=client_id)

        user_client = DbUserClient.query.filter_by(
            user_id=user_id, client_id=client_id).one_or_none()

        if not user_client:
            try:
                current_app.db.session.add(DbUserClient(
                    user_id=user_id, client_id=client_id))
                current_app.db.session.commit()
            except Exception:
                current_app.db.session.rollback()
                raise
            return json_response('', 201)

        return json_response()

    if request.method == 'DELETE':
        # TODO remove all active tokens associated with user/client
        try:
            DbUserClient.query.filter_by(user_id=user_id, id=id).delete()

            current_app.db.session.commit()
        except Exception:
            current_app.db.session.rollback()
            raise

        return json_response({})
