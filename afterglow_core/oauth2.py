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

import time
import secrets

from . import app


__all__ = [
    'memory_session', 'oauth_clients', 'oauth_server', 'Token',
]


memory_engine = None
memory_session = None

Token = None

oauth_clients = {}
oauth_server = None


def _init_oauth():
    """
    Initialize Afterglow OAuth2 server

    :return: None
    """
    import sqlite3
    from sqlalchemy import Column, Integer, String, Text, create_engine, event
    import sqlalchemy.orm.session
    # noinspection PyProtectedMember
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.pool import StaticPool
    from authlib.oauth2.rfc6749 import ClientMixin
    from authlib.oauth2.rfc6749 import grants
    from authlib.oauth2.rfc7636 import CodeChallenge
    from authlib.integrations.sqla_oauth2 import (
        OAuth2AuthorizationCodeMixin, OAuth2TokenMixin, create_save_token_func)
    from authlib.integrations.flask_oauth2 import AuthorizationServer
    from .resources.users import DbUser

    global Token, memory_engine, memory_session, oauth_server

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
                    - redirect_uris: a list of redirect uris; the first one
                        is used by default
                    - consent_uri: redirect URI of the user consent page

                Optional attributes::
                    - description: client description
                    - default_scopes: list of default scopes of the client
                    - token_endpoint_auth_method: RFC7591 token endpoint
                        authentication method: "none" (public client),
                        "client_secret_post" (client uses the HTTP POST
                        parameters), or "client_secret_basic" (client uses basic
                        HTTP auth)
                    - allowed_grant_types: list of allowed grant types,
                        including "authorization_code", "implicit",
                        "client_credentials", and "password"
            """
            for name, val in kwargs.items():
                setattr(self, name, val)

            if self.name is None:
                raise ValueError('Missing OAuth client name')
            if self.client_id is None:
                raise ValueError('Missing OAuth client ID')

            if not self.redirect_uris:
                raise ValueError('Missing OAuth redirect URIs')

            if self.token_endpoint_auth_method not in (
                    'none', 'client_secret_post', 'client_secret_basic'):
                raise ValueError('Invalid token endpoint auth method')

            if self.token_endpoint_auth_method != 'none' and \
                    self.client_secret is None:
                raise ValueError('Missing OAuth client secret')

            if self.description is None:
                self.description = self.name

        def get_client_id(self) -> str:
            """Return ID of the client"""
            return self.client_id

        def get_default_redirect_uri(self) -> str:
            """Return client default redirect_uri"""
            return self.redirect_uris[0]

        def get_allowed_scope(self, scope: str) -> str:
            """
            Return requested scopes which are supported by this client

            :param scope: requested scope(s), multiple scopes are separated
                by spaces
            """
            if scope is None:
                scope = ''
            return ' '.join({s for s in scope.split()
                             if s in self.default_scopes})

        def check_redirect_uri(self, redirect_uri: str) -> bool:
            """Validate redirect_uri parameter in authorization endpoints

            :param redirect_uri: URL string for redirecting.

            :return: True if valid redirect URI
            """
            return redirect_uri in self.redirect_uris

        def has_client_secret(self) -> bool:
            """Does the client has a secret?"""
            return bool(self.client_secret)

        def check_client_secret(self, client_secret: str) -> bool:
            """Validate client_secret

            :param client_secret: client secret

            :return: True if client secret matches the stored value
            """
            return client_secret == self.client_secret

        def check_token_endpoint_auth_method(self, method: str) -> bool:
            """Validate token endpoint auth method

            :param method: token endpoint auth method

            :return: True if the given token endpoint auth method matches
                the one for the server
            """
            return method == self.token_endpoint_auth_method

        def check_response_type(self, response_type: str) -> bool:
            """Check that the client can handle the given response_type

            :param response_type: requested response_type

            :return: True if a valid response type
            """
            return response_type in ('code', 'token')

        def check_grant_type(self, grant_type: str) -> bool:
            """Check that the client can handle the given grant_type

            :param grant_type: requested grant type

            :return: True if grant type is supported by client
            """
            return grant_type in self.allowed_grant_types

    # noinspection PyPep8Naming
    Base = declarative_base()

    class OAuth2AuthorizationCode(Base, OAuth2AuthorizationCodeMixin):
        __tablename__ = 'oauth_codes'

        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)

        @property
        def user(self) -> DbUser:
            return DbUser.query.get(self.user_id)

    class _Token(Base, OAuth2TokenMixin):
        """
        Token object; stored in the memory database
        """
        __tablename__ = 'oauth_tokens'

        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)
        # override Mixin to set default=oauth2
        token_type = Column(String(40), default='oauth2')
        note = Column(Text, default='')

        @property
        def user(self) -> DbUser:
            return DbUser.query.get(self.user_id)

        @property
        def active(self) -> bool:
            if self.revoked:
                return False
            if not self.expires_in:
                return True
            return self.issued_at + self.expires_in >= time.time()

        def is_refresh_token_active(self):
            if self.revoked:
                return False
            expires_at = self.issued_at + \
                app.config.get('REFRESH_TOKEN_EXPIRES')
            return expires_at >= time.time()

    Token = _Token

    class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
        def save_authorization_code(self, code, req) -> None:
            """Save authorization_code for later use"""
            sess = memory_session()
            try:
                # noinspection PyArgumentList
                code_challenge = request.data.get('code_challenge')
                code_challenge_method = request.data.get(
                    'code_challenge_method')

                sess.add(OAuth2AuthorizationCode(
                    code=code,
                    client_id=req.client.client_id,
                    redirect_uri=req.redirect_uri,
                    scope=req.scope,
                    user_id=req.user.id,
                    code_challenge=code_challenge,
                    code_challenge_method=code_challenge_method,
                ))
                sess.commit()
            except Exception:
                sess.rollback()
                raise
            finally:
                sess.close()

        def query_authorization_code(self, code, client) \
                -> OAuth2AuthorizationCode:
            sess = memory_session()
            item = sess.query(OAuth2AuthorizationCode).filter_by(
                code=code, client_id=client.client_id).first()
            if item and not item.is_expired():
                return item

        def delete_authorization_code(self, authorization_code) -> None:
            sess = memory_session()
            try:
                sess.delete(authorization_code)
                sess.commit()
            except Exception:
                sess.rollback()
                raise
            finally:
                sess.close()

        def authenticate_user(self, authorization_code) -> DbUser:
            return DbUser.query.get(authorization_code.user_id)

    class RefreshTokenGrant(grants.RefreshTokenGrant):
        def authenticate_refresh_token(self, refresh_token) -> Token:
            sess = memory_session()
            token = sess.query(Token) \
                .filter_by(refresh_token=refresh_token) \
                .first()
            if token and token.is_refresh_token_active():
                return token

        def authenticate_user(self, credential) -> DbUser:
            return credential.user

        def revoke_old_credential(self, credential) -> None:
            credential.revoked = True
            try:
                db.session.add(credential)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    for client_def in app.config.get('OAUTH_CLIENTS', []):
        oauth_clients[client_def.get('client_id')] = OAuth2Client(**client_def)

    @event.listens_for(Engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, _rec):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.close()
    memory_engine = create_engine(
        'sqlite://',
        connect_args=dict(check_same_thread=False, isolation_level=None),
        poolclass=StaticPool)
    Base.metadata.create_all(bind=memory_engine)
    memory_session = sqlalchemy.orm.scoped_session(
        sqlalchemy.orm.session.sessionmaker(bind=memory_engine))

    def access_token_generator(*_):
        return secrets.token_hex(20)

    # Configure Afterglow OAuth2 tokens
    app.config['OAUTH2_ACCESS_TOKEN_GENERATOR'] = \
        app.config['OAUTH2_REFRESH_TOKEN_GENERATOR'] = \
        access_token_generator

    oauth_server = AuthorizationServer(
        app,
        query_client=lambda client_id: oauth_clients.get(client_id),
        save_token=create_save_token_func(memory_session, Token),
    )
    oauth_server.register_grant(grants.ImplicitGrant)
    oauth_server.register_grant(grants.ClientCredentialsGrant)
    oauth_server.register_grant(
        AuthorizationCodeGrant, [CodeChallenge(required=True)])
    oauth_server.register_grant(RefreshTokenGrant)

    app.logger.info('Initialized Afterglow OAuth2 Service')


if app.config.get('AUTH_ENABLED'):
    _init_oauth()
