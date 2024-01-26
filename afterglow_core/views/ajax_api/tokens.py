"""
Afterglow Core: settings routes
"""

import secrets

from flask import Response, request

from ... import json_response
from ...auth import auth_required
from ...resources import users
from ...schemas.api.v1 import TokenSchema
from ...errors import ValidationError
from ...errors.auth import UnknownTokenError
from . import ajax_blp as blp


@blp.route('/tokens', methods=['GET', 'POST'])
@auth_required
def tokens() -> Response:
    """
    Return or create personal access tokens

    :return:
        GET /api/v1/tokens: list of tokens
        POST /api/v1/tokens: token
    """
    if request.method == 'GET':
        return json_response(
            [TokenSchema(tok, only=('id', 'note'))
             for tok in request.user.tokens])
    if request.method == 'POST':
        note = request.args.get('note')
        if not note or note == '':
            raise ValidationError('note', 'Note cannot be empty')

        access_token = secrets.token_hex(20)

        personal_token = users.DbPersistentToken(
            access_token=access_token,
            user_id=request.user.id,
            note=note,
        )
        try:
            users.db.session.add(personal_token)
            users.db.session.commit()
        except Exception:
            # noinspection PyBroadException
            try:
                users.db.session.rollback()
            except Exception:
                pass
            raise

        return json_response(TokenSchema(personal_token), 201)


@blp.route('/tokens/<int:token_id>', methods=['DELETE'])
@auth_required
def token(token_id: int) -> Response:
    """
    Delete personal access token

    :return:
        DELETE /api/v1/tokens/[token id]: empty response
    """
    if request.method == 'DELETE':
        personal_token = users.DbPersistentToken.query \
            .filter_by(
                token_type='personal',
                user_id=request.user.id,
                id=token_id)\
            .one_or_none()

        if not personal_token:
            raise UnknownTokenError()

        try:
            users.db.session.delete(personal_token)
            users.db.session.commit()
        except Exception:
            # noinspection PyBroadException
            try:
                users.db.session.rollback()
            except Exception:
                pass
            raise

        return json_response()
