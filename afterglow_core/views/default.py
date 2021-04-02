"""
Afterglow Core: top-level and initialization routes
"""

import json

from flask import Response, request, render_template, redirect, url_for
from flask_security.utils import hash_password, verify_password

from .. import app, json_response
from ..auth import (
    auth_required, clear_access_cookies, oauth_plugins, authenticate,
    set_access_cookies)
from ..resources.users import DbUser, DbRole, DbIdentity, db
from ..schemas.api.v1 import UserSchema
from ..errors import ValidationError, MissingFieldError
from ..errors.auth import (
    HttpAuthFailedError, NotInitializedError, UnknownAuthMethodError,
    NotAuthenticatedError, InitPageNotAvailableError)


__all__ = []




# @app.route('/login', methods=['POST'])
# def login() -> Response:
#     """
#     Login to Afterglow

#     GET|POST /auth/login
#         - login to Afterglow; authentication required using any of the methods
#           defined in USER_AUTH

#     :return: empty response with "afterglow_core_access_token" cookie
#         if successfully logged in
#     """
#     # TODO Ensure CORS is disabled for POSTS to this endpoint
#     # TODO Allow additional domains for cookies to be specified in server config

#     next_url = request.args.get('next')
#     if not next_url:
#         next_url = url_for('default')

#     # if request.method == 'GET':
#     #     try:
#     #         authenticate()
#     #         return redirect(next_url)
#     #     except NotAuthenticatedError:
#     #         pass

#     # Do not allow login if Afterglow Core has not yet been configured
#     if DbUser.query.count() == 0:
#         return redirect(url_for('initialize'))

#         # raise NotInitializedError()

#     # if request.method == 'GET':
#     #     return render_template(
#     #         'login.html.j2', oauth_plugins=oauth_plugins.values(),
#     #         next_url=next_url)

#     username = request.args.get('username')
#     if not username:
#         raise ValidationError('username', 'Username cannot be empty')

#     password = request.args.get('password')
#     if not password:
#         raise ValidationError('password', 'Password cannot be empty')

#     user = DbUser.query.filter_by(username=username).one_or_none()
#     if user is None:
#         raise HttpAuthFailedError()

#     if not verify_password(password, user.password):
#         raise HttpAuthFailedError()

#     # set token cookies
#     request.user = user

#     return set_access_cookies(json_response())





# @app.route('/logout', methods=['POST'])
# def logout() -> Response:
#     """
#     Logout from Afterglow

#     GET|POST /auth/logout
#         - log the current user out

#     :return: empty JSON response
#     """
#     return clear_access_cookies(redirect(url_for('login')))
