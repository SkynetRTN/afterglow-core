"""
Afterglow Core: settings routes
"""

import secrets

from flask import request, render_template, redirect, url_for
from flask_security.utils import verify_password

from . import url_prefix
from .... import app, json_response
from ....auth import (
    auth_required, clear_access_cookies, oauth_plugins,
    set_access_cookies)
from ....users import User, PersistentToken, db
from ....models.user import TokenSchema
from ....errors import ValidationError
from ....errors.auth import (
    HttpAuthFailedError, NotInitializedError, UnknownTokenError)


@app.route(url_prefix + 'tokens', methods=['GET', 'POST'])
@auth_required
def tokens():
    """
    Return/Create personal access tokens

    :return:
        GET /api/v1/tokens: JSON object {"items": list of tokens}
        POST /api/v1/tokens: token
    :rtype: flask.Response
    """
    if request.method == 'GET':
        return json_response({
            'items': TokenSchema(only=('id', 'note')).dump(
                request.user.tokens, many=True)
        })
    if request.method == 'POST':
        note = request.args.get('note')
        if not note or note == '':
            raise ValidationError('note', 'Note cannot be empty')

        access_token = secrets.token_hex(20)

        personal_token = PersistentToken(
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

        return json_response(TokenSchema().dump(personal_token), 201)
        

@app.route(url_prefix + 'tokens/<int:token_id>', methods=['DELETE'])
@auth_required
def token(token_id: int = None):
    """
    Delete personal access tokens

    :return:
        DELETE /settings/tokens/[token id]: empty response
    :rtype: flask.Response
    """
    if request.method == 'DELETE':
        personal_token = PersistentToken.query\
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