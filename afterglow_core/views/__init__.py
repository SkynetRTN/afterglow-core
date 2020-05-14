"""
Afterglow Core: subpackage containing all Flask app routes
"""

from .api import *

from .. import app
if app.config.get('AUTH_ENABLED'):
    from .default import *
    from .oauth2 import *
    from .users import *
del app
