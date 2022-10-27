"""
Afterglow Core: settings routes
"""

from flask import Response

from flask import current_app as app
from ... import json_response
from ...resources.users import DbUser
from . import url_prefix


@app.route(url_prefix + 'server_status', methods=['GET'])
def server_status() -> Response:
    """
    Return status of server

    :return:
        GET /ajax/server_status: server status
    """
    # TODO: import version number from module

    return json_response({
        "initialized": DbUser.query.count() != 0,
        "version": "1.0.1"
    })
