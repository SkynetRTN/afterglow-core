"""
Afterglow Core: settings routes
"""

from flask import Response

from ... import json_response
from ...auth import auth_required
from ...oauth2 import oauth_clients
from ...errors.oauth2 import UnknownClientError
from . import ajax_blp as blp


@blp.route('/oauth2/clients/<client_id>', methods=['GET'])
@auth_required
def oauth2_clients(client_id: str) -> Response:
    """
    Return OAuth2 client applications

    :return:
        GET /ajax/oauth2/clients: list of OAuth2 clients
    """

    client = next(
        (c for c in oauth_clients.values() if c.client_id == client_id), None)

    if not client:
        raise UnknownClientError()

    return json_response(dict(
        id=client.client_id,
        name=client.name,
        description=client.description,
        icon=client.icon))
