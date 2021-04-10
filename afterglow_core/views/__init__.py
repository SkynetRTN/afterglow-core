"""
Afterglow Core: subpackage containing all Flask app routes
"""

from . import public_api

from .. import app
if app.config.get('AUTH_ENABLED'):
    from . import ajax_api, admin, default, oauth2, settings
del app
