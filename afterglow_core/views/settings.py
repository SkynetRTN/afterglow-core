"""
Afterglow Core: settings routes
"""

from flask import render_template

from .. import app
from ..auth import auth_required


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
