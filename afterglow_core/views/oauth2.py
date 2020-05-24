"""
Afterglow Core: OAuth2 server routes
"""

from flask import redirect, request, url_for, render_template
from .. import app
from ..errors import MissingFieldError
from ..errors.oauth2 import UnknownClientError
from ..auth import auth_required
from ..oauth2 import oauth_clients, oauth_server
from ..users import UserClient


@app.route('/oauth2/authorize', methods=['GET'])
@auth_required(allow_redirect=True)
def oauth2_authorize():
    client_id = request.args.get('client_id')
    if not client_id:
        raise MissingFieldError('client_id')

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


@app.route('/oauth2/consent', methods=['GET'])
@auth_required(allow_redirect=True)
def oauth2_consent():
    client_id = request.args.get('client_id')
    if not client_id:
        raise MissingFieldError('client_id')

    if client_id not in oauth_clients:
        raise UnknownClientError(id=client_id)

    client = oauth_clients[client_id]

    if request.method == 'GET':
        return render_template(
            'oauth2/consent.html.j2', oauth_client=client,
            next_url=request.args.get('next'))
