"""
Afterglow Core: OAuth2 server routes
"""

from urllib.parse import urlencode
from flask import Blueprint, Flask, current_app, redirect, request

from ...auth import auth_required
from ...oauth2 import oauth_server
from ...resources import users
from ...errors import MissingFieldError


__all__ = ['register']


blp = Blueprint('oauth2', __name__, url_prefix='/oauth2')


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    app.register_blueprint(blp)


@blp.route('/authorize', methods=['GET'])
@auth_required(allow_redirect=True)
def oauth2_authorize():
    client_id = request.args.get('client_id')
    if not client_id:
        raise MissingFieldError('client_id')

    # Check that the user allowed the client
    if not users.DbUserClient.query.filter_by(
            user_id=request.user.id, client_id=client_id).count():
        # Redirect users to consent page if the client was not confirmed yet
        dashboard_prefix = current_app.config.get("DASHBOARD_PREFIX")
        args = urlencode(dict(client_id=client_id, next=request.url))
        return redirect(
            '{dashboard_prefix}/oauth2/consent?{args}'
            .format(dashboard_prefix=dashboard_prefix, args=args))

    return oauth_server.create_authorization_response(grant_user=request.user)


@blp.route('/token', methods=['POST'])
def oauth2_token():
    return oauth_server.create_token_response()
