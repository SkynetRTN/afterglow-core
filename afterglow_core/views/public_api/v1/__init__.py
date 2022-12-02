"""
Afterglow Core: API version 1
"""

from flask import Flask

__all__ = ['register', 'url_prefix']

__version__ = 1, 0, 1

url_prefix = '/api/v{0}/'.format(__version__[0])


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    from .catalogs import register
    register(app)

    from .data_files import register
    register(app)

    from .data_providers import register
    register(app)

    from .field_cals import register
    register(app)

    from .imaging_surveys import register
    register(app)

    from .jobs import register
    register(app)

    from .users import register
    register(app)
