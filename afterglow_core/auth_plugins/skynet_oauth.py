"""
Afterglow Core: Skynet OAuth authentication plugin
"""

import requests
from urllib.parse import urljoin
from typing import Optional

from .. import app
from . import OAuthServerPluginBase, OAuthToken


__all__ = ['SkynetOAuthPlugin']


class SkynetOAuthPlugin(OAuthServerPluginBase):
    """
    Skynet OAuth2 plugin (server-side flow)
    """
    name = 'skynet'

    base_url = None

    def __init__(self, description: Optional[str] = 'Login via Skynet',
                 icon: Optional[str] = 'skynet_btn_icon.png',
                 register_users: Optional[bool] = None,
                 base_url: str = 'https://api.skynet.unc.edu/2.0/',
                 access_token_url: str = 'https://skynet.unc.edu/oauth2/token',
                 authorize_url: str =
                 'https://skynet.unc.edu/oauth2/authorization_code',
                 client_id: str = None, client_secret: str = None,
                 request_token_params: Optional[dict] = None):
        """
        Initialize Skynet OAuth2 plugin

        :param description: plugin description
        :param register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param base_url: Skynet API URL
        :param access_token_url: URL for token exchange
        :param authorize_url: URL for authorization (needed by client)
        :param client_id: client ID
        :param client_secret: client secret
        :param request_token_params: additional token exchange parameters
        """
        if not request_token_params:
            request_token_params = {
                'response_type': 'code',
            }

        # Always set id=name (required by the local Skynet data provider)
        super(SkynetOAuthPlugin, self).__init__(
            self.name, description=description, icon=icon,
            register_users=register_users, authorize_url=authorize_url,
            access_token_url=access_token_url, client_id=client_id,
            client_secret=client_secret,
            request_token_params=request_token_params)

        self.base_url = base_url

    def get_user(self, token: OAuthToken) -> dict:
        """
        Return the user's Skynet username given the access token

        :param token: provider API token object

        :return: user profile
        """
        user = requests.get(
            urljoin(self.base_url, 'users'),
            headers={
                'Authorization': 'Bearer {}'.format(token.access),
            }, verify=False if app.config.get('DEBUG') else True).json()

        pf = dict(
            id=user['id'],
            username=user['username'],
        )
        if user.get('firstName'):
            pf['first_name'] = user['firstName']
        if user.get('lastName'):
            pf['last_name'] = user['lastName']
        if user.get('email'):
            pf['email'] = user['email']
        if user.get('birthdate'):
            pf['birth_date'] = user['birthdate']

        return pf
