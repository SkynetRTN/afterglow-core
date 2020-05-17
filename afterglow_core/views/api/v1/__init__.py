"""
Afterglow Core: API version 1
"""

__version__ = 1, 0, 1

url_prefix = '/api/v{0}/'.format(__version__[0])

from . import (
    catalogs, data_files, data_providers, field_cals, imaging_surveys, jobs,
    photometry,
)

from .... import app
if app.config.get('AUTH_ENABLED'):
    from . import users
del app
