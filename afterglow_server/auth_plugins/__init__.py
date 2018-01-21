"""
Afterglow Access Server: auth plugin package

An authentication plugin must subclass :class:`AuthPlugin` and implement its
get_user() method.
"""

from __future__ import absolute_import, division, print_function
from marshmallow.fields import String
from .. import Resource, errors


__all__ = ['AuthPlugin']


class AuthPlugin(Resource):
    """
    Base class for JSON-serializable authentication plugins

    Plugin modules are placed in the :mod:`auth_plugins` subpackage and must
    subclass from :class:`AuthPlugin`, e.g.

    class MyAuthPlugin(AuthPlugin):
        name = 'my_auth'

        def get_user(self):
            ...

    Attributes::
        id: unique ID of the auth plugin; assigned in the plugin configuration
        name: data provider name; can be used by the clients in requests
            like GET /auth/[id]/...
        type: auth type (e.g. "http" or "oauth2")
        description: description of the auth method
        register_users: automatically register authenticated users if missing
            from the local user database; defaults to
            REGISTER_AUTHENTICATED_USERS conf option

    Methods::
        get_user(): return the authenticated user's username
        logout(): discard the currently logged in user info
    """
    __get_view__ = 'auth_plugins_view'

    id = String(default=None)
    name = String(default=None)
    type = String(default=None)
    description = String(default=None)
    register_users = String(default=None)

    def __init__(self, id=None, description=None, register_users=None):
        """
        Initialize OAuth plugin

        :param str id: plugin ID
        :param str description: plugin description
        :param bool register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        """
        super(AuthPlugin, self).__init__()

        if id is None:
            self.id = self.name
        else:
            self.id = id

        if description is None:
            if self.description is None:
                self.description = self.name
        else:
            self.description = description

        if self.register_users is None:
            self.register_users = register_users

    def get_user(self):
        """
        Return the username of the authenticated user; raise some
        :class:`afterglow_server.errors.AfterglowError` if the user is not
        authenticated

        :return: authenticated user's username
        :rtype: str
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_user')

    def logout(self):
        """
        Optional user logout function that discards the current user info

        :return: None
        """
        pass
