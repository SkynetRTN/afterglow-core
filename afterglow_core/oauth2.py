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

Additionally, the user must set the OAUTH2_PROVIDER_ERROR_URI option
to redirect OAuth2 errors. OAUTH2_PROVIDER_TOKEN_EXPIRES_IN controls the token
expiration time.
"""

import time
import secrets

from flask import current_app, request


__all__ = [
    'init_oauth', 'oauth_clients', 'oauth_server',
]


oauth_clients = {}
oauth_server = None


# noinspection PyRedeclaration
def init_oauth():
    """
    Initialize Afterglow OAuth2 server

    :return: None
    """
    from authlib.oauth2.rfc6749 import ClientMixin
    from authlib.oauth2.rfc6749 import grants
    from authlib.oauth2.rfc7636 import CodeChallenge
    from authlib.integrations.sqla_oauth2 import create_save_token_func
    from authlib.integrations.flask_oauth2 import AuthorizationServer
    from .resources import users

    global oauth_server

    db = users.db

    # noinspection PyAbstractClass
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
                        parameters), or "client_secret_basic" (client uses
                        basic HTTP auth)
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

    class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
        def save_authorization_code(self, code, req) -> None:
            """Save authorization_code for later use"""
            try:
                # noinspection PyArgumentList
                code_challenge = request.data.get('code_challenge')
                code_challenge_method = request.data.get(
                    'code_challenge_method')

                # noinspection PyArgumentList
                db.session.add(users.OAuth2AuthorizationCode(
                    code=code,
                    client_id=req.client.client_id,
                    redirect_uri=req.redirect_uri,
                    scope=req.scope,
                    user_id=req.user.id,
                    code_challenge=code_challenge,
                    code_challenge_method=code_challenge_method,
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

        def query_authorization_code(self, code, client) \
                -> users.OAuth2AuthorizationCode:
            item = users.OAuth2AuthorizationCode.query.filter_by(
                code=code, client_id=client.client_id).first()
            if item and not item.is_expired():
                return item

        def delete_authorization_code(self, authorization_code) -> None:
            try:
                db.session.delete(authorization_code)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

        def authenticate_user(self, authorization_code) -> users.DbUser:
            return users.DbUser.query.get(authorization_code.user_id)

    class RefreshTokenGrant(grants.RefreshTokenGrant):
        def authenticate_refresh_token(self, refresh_token) -> users.Token:
            token = users.Token.query \
                .filter_by(refresh_token=refresh_token) \
                .first()
            if token and token.is_refresh_token_active():
                return token

        def authenticate_user(self, credential: users.Token) -> users.DbUser:
            return credential.user

        def revoke_old_credential(self, credential: users.Token) -> None:
            credential.access_token_revoked_at = \
                credential.refresh_token_revoked_at = int(time.time())
            try:
                db.session.add(credential)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    for client_def in current_app.config.get('OAUTH_CLIENTS', []):
        oauth_clients[client_def.get('client_id')] = OAuth2Client(**client_def)

    def access_token_generator(*_):
        return secrets.token_hex(20)

    # Configure Afterglow OAuth2 tokens
    current_app.config['OAUTH2_ACCESS_TOKEN_GENERATOR'] = \
        current_app.config['OAUTH2_REFRESH_TOKEN_GENERATOR'] = \
        access_token_generator

    oauth_server = AuthorizationServer(
        current_app,
        query_client=lambda client_id: oauth_clients.get(client_id),
        save_token=create_save_token_func(db.session, users.Token),
    )
    oauth_server.register_grant(grants.ImplicitGrant)
    oauth_server.register_grant(grants.ClientCredentialsGrant)
    oauth_server.register_grant(
        AuthorizationCodeGrant, [CodeChallenge(required=True)])
    oauth_server.register_grant(RefreshTokenGrant)

    current_app.logger.info('Initialized Afterglow OAuth2 Service')
