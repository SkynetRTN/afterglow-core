"""
Afterglow Core: settings routes
"""

import secrets

from flask import request, render_template, redirect, url_for
from flask_security.utils import verify_password

from .. import app, json_response
from ..auth import (
    auth_required, clear_access_cookies, oauth_plugins,
    set_access_cookies)
from ..users import User, PersistentToken, db
from ..models.user import TokenSchema
from ..errors import ValidationError
from ..errors.auth import (
    HttpAuthFailedError, NotInitializedError, UnknownTokenError)




@app.route('/settings/tokens', methods=['GET'])
@auth_required
def settings_tokens():
    """
    Return token management page

    :return:
        GET /settings/tokens: JSON object {"items": list of tokens}
    :rtype: flask.Response
    """
    return render_template('settings/tokens.html.j2')
