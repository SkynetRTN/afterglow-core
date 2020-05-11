"""
Afterglow Core: OAuth2 server routes
"""

from __future__ import absolute_import, division, print_function

from flask import redirect, request, url_for

from .. import app
from .. import errors
from ..auth import auth_required
from ..oauth2 import oauth_server
from ..users import UserClient


@app.route('/oauth2/authorize')
@auth_required('user', allow_redirect=True)
def oauth2_authorize():
    client_id = request.args.get('client_id')
    if not client_id:
        raise errors.MissingFieldError('client_id')

    # Check that the user allowed the client
    if not UserClient.query.filter_by(
            user_id=request.user.id, client_id=client_id).count():
        # Redirect users to consent page if the client was not confirmed yet
        return redirect(url_for(
            'oauth2_consent', client_id=client_id, next=request.url))

    return oauth_server.create_authorization_response(grant_user=request.user)


@app.route('/oauth2/token', methods=['POST'])
def oauth2_token():
    return oauth_server.create_token_response()
