"""
Afterglow Access Server: Skynet OAuth authentication plugins (both client- and
server-side flow)
"""

from __future__ import absolute_import, division, print_function

import sys
import json
import requests

from . import OAuthPlugin, OAuthUserProfile

if sys.version_info.major < 3:
    # noinspection PyCompatibility
    from urlparse import urljoin
else:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.parse import urljoin


__all__ = ['SkynetOAuthPlugin']

class SkynetOAuthPlugin(OAuthPlugin):
    """
    Skynet OAuth2 plugin (server-side flow)
    """
    name = 'skynet'

    base_url = None

    def __init__(self, description='Login via Skynet', icon=None, register_users=None,
                 base_url='https://api.skynet.unc.edu/2.0/',
                 access_token_url='https://skynet.unc.edu/oauth2/token',
                 authorize_url='https://skynet.unc.edu/oauth2/'
                               'authorization_code',
                 client_id=None, client_secret=None, request_token_params=None):
        """
        Initialize Skynet OAuth2 plugin

        :param str description: plugin description
        :param bool register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param str base_url: Skynet API URL
        :param str access_token_url: URL for token exchange
        :param str authorize_url: URL for authorization (needed by client)
        :param str client_id: client ID
        :param str client_secret: client secret
        :param dict request_token_params: additional token exchange parameters
        """
        # Always set id=name (required by the local Skynet data provider)
        super(SkynetOAuthPlugin, self).__init__(
            self.name, description=description, icon=icon, register_users=register_users,
            authorize_url=authorize_url, access_token_url=access_token_url,
            client_id=client_id, client_secret=client_secret,
            request_token_params=request_token_params)

        self.base_url = base_url

    def get_user_profile(self, token):
        """
        Return the user's Skynet username given the access token

        :param str access_token: provider API access token
        :param str | None refresh_token: refresh token
        :param datetime.datetime | None expires: UTC time of access token
            expiration

        :return: username of the authorized user
        :rtype: str
        """
        user = requests.get(
            urljoin(self.base_url, 'users'),
            headers={
                'Authorization': 'Bearer {}'.format(token.access),
            }).json()

        pf = OAuthUserProfile()
        pf.id = user['id']
        pf.username = user['username']
        pf.first_name = user['firstName']
        pf.last_name = user['lastName']
        pf.email = user['email']

        return pf

