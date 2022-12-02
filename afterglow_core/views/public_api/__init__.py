"""
Afterglow Core: views for all public API versions
"""

from flask import Flask

__all__ = ['register']


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    from .v1 import register
    register(app)
