"""
Afterglow Core: settings routes
"""

import secrets

from flask import Response, request
from marshmallow.fields import Integer, String

from flask import current_app as app
from ... import json_response
from ...auth import auth_required
from ...resources.users import DbPersistentToken, db
from ...schemas import Resource
from ...errors import ValidationError
from ...errors.auth import UnknownTokenError
from . import url_prefix


class TokenSchema(Resource):
    __get_view__ = 'tokens'

    id: int = Integer()
    user_id: int = Integer()
    token_type: str = String()
    access_token: str = String()
    issued_at: int = Integer()
    expires_in: int = Integer()
    note: str = String()


@app.route(url_prefix + 'tokens', methods=['GET', 'POST'])
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

        personal_token = DbPersistentToken(
            access_token=access_token,
            user_id=request.user.id,
            note=note,
        )
        try:
            db.session.add(personal_token)
            db.session.commit()
        except Exception:
            # noinspection PyBroadException
            try:
                db.session.rollback()
            except Exception:
                pass
            raise

        return json_response(TokenSchema(personal_token), 201)


@app.route(url_prefix + 'tokens/<int:token_id>', methods=['DELETE'])
@auth_required
def token(token_id: int) -> Response:
    """
    Delete personal access token

    :return:
        DELETE /api/v1/tokens/[token id]: empty response
    """
    if request.method == 'DELETE':
        personal_token = DbPersistentToken.query \
            .filter_by(
                token_type='personal',
                user_id=request.user.id,
                id=token_id)\
            .one_or_none()

        if not personal_token:
            raise UnknownTokenError()

        try:
            db.session.delete(personal_token)
            db.session.commit()
        except Exception:
            # noinspection PyBroadException
            try:
                db.session.rollback()
            except Exception:
                pass
            raise

        return json_response()
