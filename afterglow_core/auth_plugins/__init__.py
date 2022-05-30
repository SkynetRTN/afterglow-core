"""
Afterglow Core: oauth plugin package

An OpenAuth2 plugin must subclass :class:`OAuthPluginBase` and implement its
methods.
"""

import sys
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from typing import Optional

from marshmallow.fields import Dict, String

from flask import url_for

from .. import app, errors
from ..schemas import AfterglowSchema
from ..errors.auth import NotAuthenticatedError


__all__ = [
    'AuthnPluginBase', 'HttpAuthPluginBase', 'OAuthServerPluginBase',
    'OAuthToken',
]


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


class AuthnPluginBase(AfterglowSchema):
    """
    Base class for all authentication plugins
    """
    __polymorphic_on__ = 'name'

    id = String(dump_default=None)
    name = String(dump_default=None)
    type = String(dump_default=None)
    description = String(dump_default=None)
    icon = String(dump_default=None)
    register_users = String(dump_default=None)

    def __init__(self, id: Optional[str] = None,
                 description: Optional[str] = None, icon: Optional[str] = None,
                 register_users: Optional[bool] = None):
        super().__init__()

        if id is None:
            self.id = self.name
        else:
            self.id = id

        if description is None:
            if self.description is None:
                self.description = self.name
        else:
            self.description = description

        if icon is not None:
            self.icon = icon
        if self.icon is None:
            self.icon = self.name

        if self.register_users is None:
            self.register_users = register_users


class HttpAuthPluginBase(AuthnPluginBase):
    """
    Class for HTTP Auth plugins
    """
    type = 'http'

    def get_user(self, username: str, password: str) -> dict:
        """
        Provider-specific user getter; implemented by HTTP auth plugin that
        retrieves the user's profile based on the provided username and password

        :param username: username
        :param password: password

        :return: user profile
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_user')


class OAuthToken:
    def __init__(self, access: str, refresh: str, expiration: datetime):
        self.access = access
        self.refresh = refresh
        self.expiration = expiration


class OAuthServerPluginBase(AuthnPluginBase):
    """
    Class for OAuth plugins
    """
    # Fields visible on the client side
    authorize_url = String(dump_default=None)
    request_token_params = Dict(dump_default=None)
    client_id = String(dump_default=None)

    # Internal fields related to access token exchange
    client_secret = None
    access_token_url = None
    access_token_method = None
    access_token_headers = None
    access_token_params = None

    def __init__(self, id: Optional[str] = None,
                 description: Optional[str] = None,
                 icon: Optional[str] = None,
                 register_users: Optional[bool] = None,
                 authorize_url: Optional[str] = None,
                 request_token_params: Optional[dict] = None,
                 client_id: str = None,
                 client_secret: str = None,
                 access_token_url: str = None,
                 access_token_method: str = 'POST',
                 access_token_headers: Optional[dict] = None,
                 access_token_params: Optional[dict] = None):
        """
        Initialize OAuth plugin

        :param id: plugin ID
        :param description: plugin description
        :param icon: plugin icon ID used by the client UI
        :param register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param authorize_url: URL for authorization (needed by client)
        :param request_token_params: additional parameters for auth code
            exchange, like scope
        :param client_id: client ID
        :param client_secret: client secret
        :param access_token_url: URL for token exchange
        :param access_token_method: HTTP method for access token URL;
            default: "POST"
        :param access_token_headers: additional headers for token exchange
        :param access_token_params: additional parameters for token exchange
        """
        super().__init__(
            id=id, description=description, icon=icon,
            register_users=register_users)

        self.type = 'oauth_server'

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

    def construct_authorize_url(self, state: Optional[dict] = None) -> str:
        """
        Generic authorization url formatter; implemented by OAuth plugin base
        that creates the OAuth server's authorization URL from state parameters

        :param state: additional application state to be added to OAuth state
            query parameter

        :return: authorization URL
        """
        if state is None:
            state = {}
        state_json = json.dumps(state)
        qs = urlencode(dict(
            state=state_json,
            redirect_uri=url_for(
                'oauth2_authorized', _external=True, plugin_id=self.id),
            client_id=self.client_id,
            **self.request_token_params))
        return '{}?{}'.format(self.authorize_url, qs)

    def get_token(self, code: str, redirect_uri: str) -> OAuthToken:
        """
        Generic token getter; implemented by OAuth plugin base that retrieves
        the token using an authorization code

        :param code: authorization code
        :param base_url: root URL

        :return: OAuthToken containing access, refresh, and expiration
        """

        args = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': redirect_uri,
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

            return OAuthToken(
                access=data.get('access_token'),
                refresh=data.get('refresh_token'),
                expiration=expires)

        except Exception as e:
            raise NotAuthenticatedError(error_msg=str(e))

    def get_user(self, token: OAuthToken) -> dict:
        """
        Provider-specific user getter; implemented by OAuth plugin that
        retrieves the user using the provider API and token

        :param token: provider API access, refresh, expiration token info

        :return: user profile
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_user')
