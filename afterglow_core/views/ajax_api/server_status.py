"""
Afterglow Core: settings routes
"""

from flask import Response

from ... import json_response
from ...resources import users
from . import ajax_blp as blp, __version__


@blp.route('/server_status', methods=['GET'])
def server_status() -> Response:
    """
    Return status of server

    :return:
        GET /ajax/server_status: server status
    """
    return json_response({
        'initialized': users.DbUser.query.count() != 0,
        'version': __version__,
    })
