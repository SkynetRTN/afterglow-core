from __future__ import absolute_import, division, print_function

import base64
import json

import requests

from . import OAuthServerPluginBase, OAuthToken, AuthnPluginUser


class GoogleOAuthPlugin(OAuthServerPluginBase):
    """
    Google OAuth2 plugin (server-side flow)
    """
    name = 'google'

    def __init__(self, id=None, description='Login via Google', icon='google',
                 register_users=False, client_id=None, client_secret=None,
                 request_token_params=None):
        """
        Initialize Google OAuth2 plugin

        :param str id: plugin ID
        :param str description: plugin description
        :param str icon: plugin icon ID used by the client UI
        :param bool register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param str client_id: client ID
        :param str client_secret: client secret
        :param dict request_token_params: additional token exchange parameters;
            Google requires at least scope="email", access_type="offline",
            response_type="code", which is the default
        """
        super(GoogleOAuthPlugin, self).__init__(
            id, description=description, icon=icon,
            register_users=register_users,
            access_token_url='https://accounts.google.com/o/oauth2/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            request_token_params=request_token_params if request_token_params
            else {
                'scope': 'email', 'access_type': 'offline',
                'response_type': 'code'},
            client_id=client_id,
            client_secret=client_secret)

    @staticmethod
    def get_user_profile(token: OAuthToken):
        """
        Return the user's Skynet username given the access token

        :param token: provider API token object

        :return: user profile
        :rtype: OAuthUserProfile
        """
        # Decode the access token (which is a JWT) and extract the email
        s = token.access[:token.access.rfind('.')]
        s = base64.decodebytes(s + '='*((4 - len(s) % 4) % 4))

        # Decode header
        i = 1
        while i <= len(s):
            try:
                json.loads(s[:i])
            except ValueError:
                i += 1
            else:
                break

        # Decode payload
        s = s[i:]
        i = 1
        while i <= len(s):
            try:
                return json.loads(s[:i])['email']
            except ValueError:
                i += 1

        # No email in the token; call the API to get it
        user = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            headers={
                'Authorization': 'Bearer {}'.format(token.access),
            }).json()

        pf = AuthnPluginUser()
        pf.id = user['email']
        pf.email = user['email']

        return pf
