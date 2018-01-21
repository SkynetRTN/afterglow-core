"""
Afterglow Access Server: Skynet OAuth authentication plugins (both client- and
server-side flow)
"""

from __future__ import absolute_import, division, print_function

import sys
import json
import requests

from .oauth_client import ClientOAuthPlugin
from .oauth_server import OAuthPlugin

if sys.version_info.major < 3:
    # noinspection PyCompatibility
    from urlparse import urljoin
else:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.parse import urljoin


__all__ = ['SkynetClientOAuthPlugin', 'SkynetOAuthPlugin']


class SkynetClientOAuthPlugin(ClientOAuthPlugin):
    """
    SkyNet OAuth2 plugin (client-side flow)
    """
    name = 'skynet_client_oauth'
    type = 'oauth2client'

    def __init__(self, description='Login via SkyNet (client-side)',
                 register_users=None,
                 base_url='https://api.skynet.unc.edu/2.0/',
                 access_token_url='https://skynet.unc.edu/oauth2/token',
                 authorize_url='https://skynet.unc.edu/oauth2/'
                 'authorization_code',
                 consumer_key=None, consumer_secret=None,
                 request_token_params=None):
        """
        Initialize SkyNet OAuth2 plugin

        :param str description: plugin description
        :param bool register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param str base_url: base URL for every request
        :param str access_token_url: URL for token exchange
        :param str authorize_url: URL for authorization
        :param str consumer_key: client ID
        :param str consumer_secret: client secret
        :param dict request_token_params: additional token exchange parameters
        """
        # Always set id=name (required by the local SkyNet data provider)
        super(SkynetClientOAuthPlugin, self).__init__(
            self.name, description=description, register_users=register_users,
            base_url=base_url,
            access_token_url=access_token_url, authorize_url=authorize_url,
            consumer_key=consumer_key, consumer_secret=consumer_secret,
            request_token_params=request_token_params if request_token_params
            else {})

    def callback(self, resp):
        """
        SkyNet authorize handler; returns the user's SkyNet username as the
        Afterglow username

        :param dict resp: result of calling
            :func:`flask_oauthlib.client.OAuthRemoteApp.authorized_response`

        :return: username of the authorized user
        :rtype: str
        """
        user = self.remote_app.get('users')
        username = json.loads(user.data)['username']

        # TODO: Add Skynet access and refresh tokens to the user db

        return username


class SkynetOAuthPlugin(OAuthPlugin):
    """
    Skynet OAuth2 plugin (server-side flow)
    """
    name = 'skynet_oauth'
    type = 'oauth2server'

    base_url = None

    def __init__(self, description='Login via Skynet', register_users=None,
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
            self.name, description=description, register_users=register_users,
            authorize_url=authorize_url, access_token_url=access_token_url,
            client_id=client_id, client_secret=client_secret,
            request_token_params=request_token_params)

        self.base_url = base_url

    def get_username(self, access_token, refresh_token, expires):
        """
        Return the user's Skynet username given the access token

        :param str access_token: provider API access token
        :param str | None refresh_token: refresh token
        :param datetime.datetime | None expires: UTC time of access token
            expiration

        :return: username of the authorized user
        :rtype: str
        """
        username = requests.get(
            urljoin(self.base_url, 'users'),
            headers={
                'Authorization': 'Bearer {}'.format(access_token),
            }).json()['username']

        # TODO: Add Skynet access and refresh tokens to the user db

        return username
