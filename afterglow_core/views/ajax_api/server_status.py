"""
Afterglow Core: settings routes
"""

from flask import Response

from ... import json_response
from ...resources.users import DbUser
from . import ajax_blp as blp, __version__


@blp.route('/server_status', methods=['GET'])
def server_status() -> Response:
    """
    Return status of server

    :return:
        GET /ajax/server_status: server status
    """
    # TODO: import version number from module

    return json_response({
        'initialized': DbUser.query.count() != 0,
        'version': '.'.join(str(i) for i in __version__)
    })
