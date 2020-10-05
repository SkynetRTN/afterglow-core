"""
Afterglow Core: Google OAuth authentication plugin
"""

import base64
import json
from typing import Optional

import requests

from . import OAuthServerPluginBase, OAuthToken


class GoogleOAuthPlugin(OAuthServerPluginBase):
    """
    Google OAuth2 plugin (server-side flow)
    """
    name = 'google'

    def __init__(self, id: Optional[str] = None,
                 description: Optional[str] = 'Login via Google',
                 icon: Optional[str] = 'google_btn_icon.png',
                 register_users: Optional[bool] = False,
                 client_id: str = None,
                 client_secret: str = None,
                 request_token_params: Optional[dict] = None):
        """
        Initialize Google OAuth2 plugin

        :param id: plugin ID
        :param description: plugin description
        :param icon: plugin icon ID used by the client UI
        :param register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param client_id: client ID
        :param client_secret: client secret
        :param request_token_params: additional token exchange parameters;
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

    def get_user(self, token: OAuthToken) -> dict:
        """
        Return the user's Google profile given the access token

        :param token: provider API token object

        :return: user profile
        """
        # Decode the access token (which is a JWT) and extract the email
        s = token.access[:token.access.rfind('.')]
        s = base64.decodebytes(s.encode('ascii') + b'='*((4 - len(s) % 4) % 4))

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

        return dict(
            id=user['email'],
            email=user['email'],
        )
