"""
Afterglow Core: subpackage containing all Flask app routes
"""

from . import public_api

from flask import current_app as app
if app.config.get('AUTH_ENABLED'):
    from .ajax_api import *
    from .oauth2 import *
del app
