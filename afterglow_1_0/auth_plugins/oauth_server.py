"""
Afterglow Access Server: OAuth 1/2 authentication plugins (server-side flow)

The client must provide the authorization code in the "code" request parameter
supplied to auth/login, as well as the callback URI in the "redirect_uri"
parameter.
"""

from __future__ import absolute_import, division, print_function

import sys
import requests
import base64
import json
from datetime import datetime, timedelta

from marshmallow.fields import Dict, String

from flask import request

from .. import app, auth, errors
from . import AuthPlugin


__all__ = ['OAuthPlugin', 'GoogleOAuthPlugin']


if sys.version_info < (3, 1):
    # noinspection PyDeprecation
    base64_decode = base64.decodestring
else:
    base64_decode = base64.decodebytes

if app.config.get('DEBUG'):
    # Skip SSL certificate validation in debug mode
    if sys.version_info[0] < 3:
        # noinspection PyCompatibility,PyUnresolvedReferences
        from urllib2 import HTTPSHandler, build_opener, install_opener
    else:
        # noinspection PyCompatibility,PyUnresolvedReferences
        from urllib.request import HTTPSHandler, build_opener, install_opener
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    install_opener(build_opener(HTTPSHandler(context=ctx)))


class OAuthPlugin(AuthPlugin):
    """
    Base class for OAuth plugins (server-side flow)
    """
    # Fields visible on the client side
    authorize_url = String(default=None)
    request_token_params = Dict(default=None)
    client_id = String(default=None)

    # Internal fields related to access token exchange
    client_secret = None
    access_token_url = None
    access_token_method = None
    access_token_headers = None
    access_token_params = None

    def __init__(self, id=None, description=None, icon=None,
                 register_users=None, authorize_url=None,
                 request_token_params=None, client_id=None,
                 client_secret=None, access_token_url=None,
                 access_token_method='POST', access_token_headers=None,
                 access_token_params=None):
        """
        Initialize OAuth plugin

        :param str id: plugin ID
        :param str description: plugin description
        :param str icon: plugin icon ID used by the client UI
        :param bool register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param str authorize_url: URL for authorization (needed by client)
        :param dict request_token_params: additional parameters for auth code
            exchange, like scope
        :param str client_id: client ID
        :param str client_secret: client secret
        :param str access_token_url: URL for token exchange
        :param str access_token_method: HTTP method for access token URL;
            default: "POST"
        :param dict access_token_headers: additional headers for token exchange
        :param dict access_token_params: additional parameters for token
            exchange
        """
        super(OAuthPlugin, self).__init__(
            id=id, description=description, icon=icon,
            register_users=register_users)

        self.authorize_url = authorize_url
        if request_token_params:
            self.request_token_params = request_token_params
        else:
            self.request_token_params = {}

        if not client_id:
            raise ValueError('Missing OAuth client ID')
        self.client_id = client_id

        if not client_secret:
            raise ValueError('Missing OAuth client secret')
        self.client_secret = str(client_secret)

        if not access_token_url:
            raise ValueError('Missing OAuth access token URL')
        self.access_token_url = str(access_token_url)

        if not access_token_method:
            raise ValueError('Missing OAuth access token method')
        access_token_method = str(access_token_method).upper()
        if access_token_method not in ('GET', 'POST'):
            raise ValueError('Invalid OAuth access token method "{}"'.format(
                access_token_method))
        self.access_token_method = access_token_method

        if access_token_headers:
            try:
                access_token_headers = dict(access_token_headers)
            except (TypeError, ValueError):
                raise ValueError(
                    'Invalid OAuth access token headers "{}"'.format(
                        access_token_headers))
        self.access_token_headers = access_token_headers

        if access_token_params:
            try:
                access_token_params = dict(access_token_params)
            except (TypeError, ValueError):
                raise ValueError(
                    'Invalid OAuth access token parameters "{}"'.format(
                        access_token_params))
        self.access_token_params = access_token_params

    def get_user(self):
        """
        Return the username of the authenticated user; raise
        :class:`NoAuthError` or :class:`AuthFailedError` if the user is not
        authenticated

        :return: authenticated user's username
        :rtype: str
        """
        # Get auth code from request parameters and send it to provider in
        # exchange for access token
        args = {
            'grant_type': 'authorization_code',
            'code': request.args.get('code'),
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': request.args.get('redirect_uri'),
        }
        if self.access_token_params:
            args.update(self.access_token_params)

        if self.access_token_method == 'POST':
            data = args
            args = None
        else:
            data = None

        try:
            resp = requests.request(
                self.access_token_method, self.access_token_url,
                params=args, data=data, headers=self.access_token_headers,
                verify=False if app.config.get('DEBUG') else None)
            if resp.status_code not in (200, 201):
                raise Exception(
                    'OAuth server returned HTTP status {}, message: {}'.format(
                        resp.status_code, resp.text))
            data = resp.json()

            # Get token expiration time
            expires = data.get('expires_in')
            if expires is not None:
                expires = datetime.utcnow() + timedelta(seconds=expires)

            # Get username using the token provided
            username = self.get_username(
                data.get('access_token'), data.get('refresh_token'), expires)
            if not username:
                raise auth.NotAuthenticatedError()
        except Exception as e:
            raise auth.NotAuthenticatedError(error_msg=str(e))

        # Authenticated successfully
        return username

    def get_username(self, access_token, refresh_token, expires):
        """
        Provider-specific username getter; implemented by OAuth plugin that
        retrieves the user's username using the provider API

        :param str access_token: provider API access token
        :param str | None refresh_token: refresh token
        :param datetime.datetime | None expires: UTC time of access token
            expiration

        :return: username of the authorized user
        :rtype: str
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='request_username')


class GoogleOAuthPlugin(OAuthPlugin):
    """
    Google OAuth2 plugin (server-side flow)
    """
    name = 'google_oauth'
    type = 'oauth2server'

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

    def get_username(self, access_token, refresh_token, expires):
        """
        Return the user's Google email address given the access token

        :param str access_token: provider API access token
        :param str | None refresh_token: refresh token
        :param datetime.datetime | None expires: UTC time of access token
            expiration

        :return: username of the authorized user
        :rtype: str
        """
        # Decode the access token (which is a JWT) and extract the email
        s = access_token[:access_token.rfind('.')]
        s = base64_decode(s + '='*((4 - len(s) % 4) % 4))

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
        return requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            headers={
                'Authorization': 'Bearer {}'.format(access_token),
            }).json()['email']
