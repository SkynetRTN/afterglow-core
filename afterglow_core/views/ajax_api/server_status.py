"""
Afterglow Core: settings routes
"""

import secrets

from flask import Response, request
from marshmallow.fields import Integer, String

from ... import app, json_response
from ...resources.users import DbUser, DbRole, DbIdentity, db

from . import url_prefix


@app.route(url_prefix + 'server_status', methods=['GET'])
def server_status() -> Response:
    """
    Return status of server

    :return:
        GET /ajax/server_status: server status
    """

    #TODO: import version number from module

    initialized = DbUser.query.count() != 0
    server_status = {
        "initialized": initialized,
        "version": "1.0.1"
    }

    return json_response(server_status)
