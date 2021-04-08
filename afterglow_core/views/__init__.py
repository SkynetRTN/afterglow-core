"""
Afterglow Core: subpackage containing all Flask app routes
"""

from .public_api import *

from .. import app
if app.config.get('AUTH_ENABLED'):
    from .ajax_api import *
    from .oauth2 import *
del app
