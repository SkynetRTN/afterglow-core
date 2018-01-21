"""
Afterglow Access Server: HTTP auth plugin
"""

from __future__ import absolute_import, division, print_function

from flask import request
from flask_security.utils import verify_password

from .. import auth
from . import AuthPlugin


__all__ = ['HttpAuthPlugin']


class HttpAuthFailedError(auth.AuthError):
    """
    HTTP authentication data (username/password or Authentication-Token header)
    missing or invalid

    Extra attributes::
        None
    """
    code = 401
    subcode = 120
    message = 'Invalid or missing username/password or authentication token'
    headers = [
        ('WWW-Authenticate',
         'Basic realm="{}"'.format('Local Afterglow Users Only'))]


class HttpAuthPlugin(AuthPlugin):
    """
    HTTP authentication plugin class
    """
    name = 'http'
    type = 'http'
    description = 'Simple HTTP Authentication'
    register_users = False

    def get_user(self):
        """
        Return the username of the authenticated user; raise
        :class:`NoAuthError` or :class:`AuthFailedError` if the user is not
        authenticated

        :return: authenticated user's username
        :rtype: str
        """
        # Check auth token
        user = auth.security.login_manager.request_callback(request)
        if not user or user.is_anonymous:
            # Check basic auth
            authorization = request.authorization
            if authorization:
                user = auth.security.datastore.find_user(
                    username=authorization.username)
                if user and not user.is_anonymous and not verify_password(
                        authorization.password, user.password):
                    raise HttpAuthFailedError()
        if not user or user.is_anonymous:
            raise HttpAuthFailedError()

        return user.username
