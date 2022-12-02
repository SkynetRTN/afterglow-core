"""
Afterglow Core: subpackage containing all Flask app routes
"""

from flask import Flask

__all__ = ['register']


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    from .public_api import register
    register(app)

    if app.config.get('AUTH_ENABLED'):
        from .ajax_api import register
        register(app)

        from .oauth2 import register
        register(app)
