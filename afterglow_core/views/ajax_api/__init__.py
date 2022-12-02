"""
Afterglow Core: AJAX API endpoints
"""

from flask import Flask

__all__ = ['register', 'url_prefix']

__version__ = 1, 0, 1

url_prefix = '/ajax/'


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    from .app_authorizations import register
    register(app)

    from .tokens import register
    register(app)

    from .sessions import register
    register(app)

    from .initialize import register
    register(app)

    from .oauth2_providers import register
    register(app)

    from .oauth2_clients import register
    register(app)

    from .server_status import register
    register(app)
