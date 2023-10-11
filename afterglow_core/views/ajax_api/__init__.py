"""
Afterglow Core: AJAX API endpoints
"""

from flask import Blueprint, Flask


__all__ = ['register', 'ajax_blp']

__version__ = '1.0.1'

ajax_blp = Blueprint('ajax_api', __name__, url_prefix='/ajax')


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    from . import (
        app_authorizations, tokens, sessions, initialize, oauth2_providers,
        oauth2_clients, http_auth_providers, server_status)
    app.register_blueprint(ajax_blp)
