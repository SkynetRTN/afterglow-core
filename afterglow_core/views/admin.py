"""
Afterglow Core: settings routes
"""

from flask import render_template

from .. import app
from ..auth import auth_required


@app.route('/admin/users', methods=['GET'])
@auth_required('admin')
def admin_users():
    """
    Return user management page

    :return:
        GET /admin/users: 
    :rtype: flask.Response
    """
    return render_template('admin/users.html.j2')
