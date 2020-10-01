"""
Afterglow Core: settings routes
"""

from flask import Response, render_template

from .. import app
from ..auth import auth_required


@app.route('/settings/tokens', methods=['GET'])
@auth_required
def settings_tokens() -> Response:
    """
    Return token management page

    :return:
        GET /settings/tokens: JSON object {"items": list of tokens}
    """
    return render_template('settings/tokens.html.j2')
