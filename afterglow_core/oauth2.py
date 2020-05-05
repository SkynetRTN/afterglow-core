"""
Afterglow Core: OAuth2 server

Afterglow OAuth2 server is enabled by defining at least one client in the
OAUTH_CLIENTS config option:

    OAUTH_CLIENTS = [
        {'client_id': '<random string>',
         'client_secret': '<random string>',
         'redirect_uris': ['<redirect URI>', ...],
         'consent_uri': '<consent URI>',
         'name': '<client name>',
         'description': '<description>',
         'is_confidential': False,
         'default_scopes': ['email', 'profile', ...],
         'allowed_grant_types': ['authorization_code'],
        },
        ...
    ]

All attributes except `client_id`, `client_secret`, `redirect_uris`, and
`consent_uri` are optional.

Additionally, the user must set the OAUTH2_PROVIDER_ERROR_URI option to redirect
OAuth2 errors. OAUTH2_PROVIDER_TOKEN_EXPIRES_IN controls the token expiration
time.
"""

from __future__ import absolute_import, division, print_function

import sys
import time
from typing import Optional

from sqlalchemy import Column, Integer, create_engine
import sqlalchemy.orm.session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
from authlib.oauth2.rfc6749 import ClientMixin
from authlib.oauth2.rfc6749 import grants
from authlib.integrations.sqla_oauth2 import (
    OAuth2AuthorizationCodeMixin, OAuth2TokenMixin, create_save_token_func)
from authlib.integrations.flask_oauth2 import AuthorizationServer

from . import app
from .users import User
from .auth import create_token

if sys.version_info.major < 3:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib import urlencode
else:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.parse import urlencode


__all__ = [
    'init_oauth', 'oauth_clients', 'create_access_token',
    'create_refresh_token',
]


class OAuth2Client(ClientMixin):
    """
    OAuth2 client definition class
    """
    name = None
    description = None
    client_id = None
    client_secret = None
    redirect_uris = None
    default_scopes = ('email',)
    token_endpoint_auth_method = 'client_secret_basic'
    allowed_grant_types = ('authorization_code', 'refresh_token',)

    def __init__(self, **kwargs):
        """
        Initialize OAuth2 client from a dictionary of attributes

        :param kwargs: client attributes; the following are required::
                - name: client name
                - client_id: a random string
                - client_secret: a random string
                - redirect_uris: a list of redirect uris; the first one is used
                    by default
                - consent_uri: redirect URI of the user consent page

            Optional attributes::
                - description: client description
                - default_scopes: list of default scopes of the client
                - token_endpoint_auth_method: RFC7591 token endpoint
                    authentication method: "none" (public client),
                    "client_secret_post" (client uses the HTTP POST parameters),
                    or "client_secret_basic" (client uses basic HTTP auth)
                - allowed_grant_types: list of allowed grant types, including
                    "authorization_code", "implicit", "client_credentials", and
                    "password"
        """
        for name, val in kwargs.items():
            setattr(self, name, val)

        if self.name is None:
            raise ValueError('Missing OAuth client name')
        if self.client_id is None:
            raise ValueError('Missing OAuth client ID')
        if self.client_secret is None:
            raise ValueError('Missing OAuth client secret')
        if not self.redirect_uris:
            raise ValueError('Missing OAuth redirect URIs')

        if self.token_endpoint_auth_method not in (
                'none', 'client_secret_post', 'client_secret_basic'):
            raise ValueError('Invalid token endpoint auth method')

        if self.description is None:
            self.description = self.name

    def get_client_id(self):
        """Return ID of the client

        :rtype: str
        """
        return self.client_id

    def get_default_redirect_uri(self):
        """Return client default redirect_uri

        :rtype: str
        """
        return self.redirect_uris[0]

    def get_allowed_scope(self, scope):
        """Return requested scopes which are supported by this client

        :param str scope: requested scope(s), multiple scopes are separated
            by spaces

        :rtype: str
        """
        return ' '.join({s for s in scope.split() if s in self.default_scopes})

    def check_redirect_uri(self, redirect_uri):
        """Validate redirect_uri parameter in authorization endpoints

        :param str redirect_uri: URL string for redirecting.

        :return: True if valid redirect URI
        :rtype: bool
        """
        return redirect_uri in self.redirect_uris

    def has_client_secret(self):
        """Does the client has a secret?

        :rtype: bool
        """
        return bool(self.client_secret)

    def check_client_secret(self, client_secret):
        """Validate client_secret

        :param str client_secret: client secret

        :return: True if client secret matches the stored value
        :rtype: bool
        """
        return client_secret == self.client_secret

    def check_token_endpoint_auth_method(self, method):
        """Validate token endpoint auth method

        :param str method: token endpoint auth method

        :return: True if the given token endpoint auth method matches the one
            for the server
        :rtype: bool
        """
        return method == self.token_endpoint_auth_method

    def check_response_type(self, response_type):
        """Check that the client can handle the given response_type

        :param str response_type: requested response_type

        :return: True if a valid response type
        :rtype: bool
        """
        return response_type in ('code', 'token')

    def check_grant_type(self, grant_type):
        """Check that the client can handle the given grant_type

        :param str grant_type: requested grant type

        :return: True if grant type is supported by client
        :rtype: bool
        """
        return grant_type in self.allowed_grant_types


Base = declarative_base()
memory_engine = None
memory_session = None  # type: Optional[sqlalchemy.orm.session.Session]


class OAuth2AuthorizationCode(Base, OAuth2AuthorizationCodeMixin):
    __tablename__ = 'oauth_codes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)

    @property
    def user(self):
        return User.query.get(self.user_id)


class OAuth2Token(Base, OAuth2TokenMixin):
    """
    Token object; stored in the memory database
    """
    __tablename__ = 'oauth_tokens'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)

    @property
    def user(self):
        return User.query.get(self.user_id)

    def is_refresh_token_active(self):
        if self.revoked:
            return False
        expires_at = self.issued_at + app.config.get('REFRESH_TOKEN_EXPIRES')
        return expires_at >= time.time()


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def save_authorization_code(self, code, req):
        """Save authorization_code for later use"""
        try:
            memory_session.add(OAuth2AuthorizationCode(
                code=code,
                client_id=req.client.client_id,
                redirect_uri=req.redirect_uri,
                scope=req.scope,
                user_id=req.user.id,
            ))
            memory_session.commit()
        except Exception:
            memory_session.rollback()
            raise

    def query_authorization_code(self, code, client):
        item = memory_session.query(OAuth2AuthorizationCode).filter_by(
            code=code, client_id=client.client_id).first()
        if item and not item.is_expired():
            return item

    def delete_authorization_code(self, authorization_code):
        try:
            memory_session.delete(authorization_code)
            memory_session.commit()
        except Exception:
            memory_session.rollback()
            raise

    def authenticate_user(self, authorization_code):
        return User.query.get(authorization_code.user_id)


class RefreshTokenGrant(grants.RefreshTokenGrant):
    def authenticate_refresh_token(self, refresh_token):
        token = memory_session.query(OAuth2Token).filter_by(
            refresh_token=refresh_token).first()
        if token and token.is_refresh_token_active():
            return token

    def authenticate_user(self, credential):
        return User.query.get(credential.user_id)

    def revoke_old_credential(self, credential):
        credential.revoked = True
        try:
            memory_session.add(credential)
            memory_session.commit()
        except Exception:
            memory_session.rollback()
            raise


oauth_clients = {}
oauth_server = None


def create_access_token(req):
    return create_token(
        req.user.id, app.config.get('ACCESS_TOKEN_EXPIRES'),
        dict(method='oauth2'))


def create_refresh_token(req):
    return create_token(
        req.user.id, app.config.get('REFRESH_TOKEN_EXPIRES'),
        dict(method='oauth2'), 'refresh')


def init_oauth():
    """
    Initialize Afterglow OAuth2 server

    :return: None
    """
    global memory_engine, memory_session, oauth_server

    for client_def in app.config['OAUTH_CLIENTS']:
        oauth_clients[client_def.get('client_id')] = OAuth2Client(**client_def)

    memory_engine = create_engine(
        'sqlite://', connect_args=dict(check_same_thread=False),
        poolclass=StaticPool)
    Base.metadata.create_all(bind=memory_engine)
    memory_session = sqlalchemy.orm.scoped_session(
        sqlalchemy.orm.session.sessionmaker(bind=memory_engine))()

    # Configure Afterglow OAuth2 tokens
    app.config['OAUTH2_ACCESS_TOKEN_GENERATOR'] = create_access_token
    app.config['OAUTH2_REFRESH_TOKEN_GENERATOR'] = create_refresh_token
    # app.config['OAUTH2_JWT_ENABLED'] = True
    # app.config['OAUTH2_JWT_ISS'] = 'Afterglow'
    # app.config['OAUTH2_JWT_KEY'] = app.config['SECRET_KEY']
    # app.config['OAUTH2_JWT_ALG'] = 'HS256'
    # app.config['OAUTH2_JWT_EXP'] = app.config.get(
    #     'ACCESS_TOKEN_EXPIRES', 3600)

    oauth_server = AuthorizationServer(
        app,
        query_client=lambda client_id: oauth_clients.get(client_id),
        save_token=create_save_token_func(memory_session, OAuth2Token),
    )
    oauth_server.register_grant(grants.ImplicitGrant)
    oauth_server.register_grant(grants.ClientCredentialsGrant)
    oauth_server.register_grant(AuthorizationCodeGrant)
    oauth_server.register_grant(RefreshTokenGrant)

    app.logger.info('Initialized Afterglow OAuth2 Service')
