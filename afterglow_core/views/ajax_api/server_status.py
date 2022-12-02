"""
Afterglow Core: settings routes
"""

from flask import Blueprint, Flask, Response

from ... import json_response
from ...resources.users import DbUser
from . import url_prefix


__all__ = ['register']


blp = Blueprint(
    'server_status', __name__, url_prefix=url_prefix + 'server_status')


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    app.register_blueprint(blp)


@blp.route('/', methods=['GET'])
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
