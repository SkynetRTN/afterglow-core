"""
Afterglow Access Server: OAuth2 server

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
from datetime import datetime, timedelta
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
from flask import redirect, request
from flask_oauthlib.provider import OAuth2Provider

from . import app, errors, json_response, url_prefix
from .users import User, db
from .auth import auth_required, authenticate, create_token, current_user

if sys.version_info.major < 3:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib import urlencode
else:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.parse import urlencode


__all__ = [
    'init_oauth', 'oauth', 'oauth_clients', 'create_access_token',
    'create_refresh_token',
]


class UnknownClientError(errors.AfterglowError):
    """
    The user requested an unknown OAuth2 client

    Extra attributes::
        id: client ID requested
    """
    code = 404
    subcode = 200
    message = 'Unknown OAuth2 client ID'


class MissingClientIdError(errors.AfterglowError):
    """
    POSTing to /oauth/user-clients with no client_id

    Extra attributes::
        None
    """
    code = 400
    subcode = 201
    message = 'Missing client ID'


class Client(object):
    """
    OAuth2 client definition class
    """
    name = None
    description = None
    client_id = None
    client_secret = None
    is_confidential = True
    redirect_uris = None
    consent_uri = None
    default_scopes = ('email',)
    allowed_grant_types = ('authorization_code', 'refresh_token',)

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

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
                - is_confidential: True for confidential (default), False for
                    public clients
                - default_scopes: list of default scopes of the client
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
        if not self.consent_uri:
            raise ValueError('Missing OAuth consent URI')

        if self.description is None:
            self.description = self.name


class UserClient(db.Model):
    """
    List of clients allowed for the user; stored in the main Afterglow database
    """
    __tablename__ = 'user_oauth_clients'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False, index=True)
    user = db.relationship('User')
    client_id = db.Column(db.String(40), nullable=False, index=True)


Base = declarative_base()
memory_engine = None
memory_session = None


class Grant(Base):
    """
    Grant object; stored in the memory database
    """
    __tablename__ = 'oauth_grants'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    client_id = Column(String(40), nullable=False)
    code = Column(String(255), index=True, nullable=False)
    redirect_uri = Column(Text)
    expires = Column(DateTime)
    _scopes = Column('scopes', Text)

    def delete(self):
        try:
            memory_session.delete(self)
            memory_session.commit()
        except Exception:
            memory_session.rollback()
            raise
        return self

    @property
    def user(self):
        return User.query.get(self.user_id)

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []


class Token(Base):
    """
    Token object; stored in the memory database
    """
    __tablename__ = 'oauth_tokens'

    id = Column(Integer, primary_key=True)
    client_id = Column(String(40), nullable=False)
    user_id = Column(Integer, nullable=False)
    token_type = Column(Text)
    access_token = Column(Text, unique=True)
    refresh_token = Column(Text, unique=True)
    expires = Column(DateTime)
    _scopes = Column('scopes', Text)

    def delete(self):
        try:
            memory_session.delete(self)
            memory_session.commit()
        except Exception:
            memory_session.rollback()
            raise
        return self

    @property
    def user(self):
        return User.query.get(self.user_id)

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []


oauth = None
oauth_clients = {}


def create_access_token(req):
    return create_token(
        req.user.username, app.config.get('ACCESS_TOKEN_EXPIRES'),
        dict(method='oauth2'))


def create_refresh_token(req):
    return create_token(
        req.user.username, app.config.get('REFRESH_TOKEN_EXPIRES'),
        dict(method='oauth2'), 'refresh'),


def init_oauth():
    global memory_engine, memory_session, oauth

    for client_def in app.config['OAUTH_CLIENTS']:
        oauth_clients[client_def.get('client_id')] = Client(**client_def)

    UserClient.metadata.create_all(bind=db.engine)

    memory_engine = create_engine(
        'sqlite://', connect_args=dict(check_same_thread=False),
        poolclass=StaticPool)
    Base.metadata.create_all(bind=memory_engine)
    memory_session = scoped_session(sessionmaker(bind=memory_engine))()

    # Make sure Afterglow OAuth2 returns the same tokens as the normal auth
    app.config['OAUTH2_PROVIDER_TOKEN_GENERATOR'] = create_access_token
    app.config['OAUTH2_PROVIDER_REFRESH_TOKEN_GENERATOR'] = create_refresh_token

    oauth = OAuth2Provider(app)

    @oauth.clientgetter
    def load_client(client_id):
        return oauth_clients.get(client_id)

    @oauth.grantgetter
    def load_grant(client_id, code):
        return memory_session.query(Grant).filter_by(
            client_id=client_id, code=code).first()

    # noinspection PyUnusedLocal
    @oauth.grantsetter
    def save_grant(client_id, code, req, *args, **kwargs):
        grant = Grant(
            client_id=client_id,
            code=code['code'],
            redirect_uri=req.redirect_uri,
            _scopes=' '.join(req.scopes),
            user_id=current_user.id,
            expires=datetime.utcnow() + timedelta(seconds=100),
        )
        try:
            memory_session.add(grant)
            memory_session.commit()
        except Exception:
            memory_session.rollback()
            raise
        return grant

    @oauth.tokengetter
    def load_token(access_token=None, refresh_token=None):
        if access_token:
            return memory_session.query(Token).filter_by(
                access_token=access_token).first()
        if refresh_token:
            return memory_session.query(Token).filter_by(
                refresh_token=refresh_token).first()

    # noinspection PyUnusedLocal
    @oauth.tokensetter
    def save_token(tok, req, *args, **kwargs):
        toks = memory_session.query(Token).filter_by(
            client_id=req.client.client_id, user_id=req.user.id)
        for t in toks:
            memory_session.delete(t)

        expires_in = tok.get('expires_in')
        if expires_in:
            expires = datetime.utcnow() + timedelta(seconds=expires_in)
        else:
            expires = None

        t = Token(
            access_token=tok.get('access_token'),
            refresh_token=tok.get('refresh_token'),
            token_type=tok['token_type'],
            _scopes=tok['scope'],
            expires=expires,
            client_id=req.client.client_id,
            user_id=req.user.id,
        )
        try:
            memory_session.add(t)
            memory_session.commit()
        except Exception:
            memory_session.rollback()
            raise
        return t

    # noinspection PyUnusedLocal
    @app.route(url_prefix + 'oauth2/authorize')
    @oauth.authorize_handler
    def oauth2_authorize(*args, **kwargs):
        # noinspection PyBroadException
        try:
            user = authenticate('user')
        except Exception:
            # Redirect unauthenticated users to consent page
            try:
                return redirect(
                    oauth_clients[kwargs['client_id']].consent_uri + '?' +
                    urlencode(dict(client_id=kwargs['client_id'],
                                   next=request.url)))
            except KeyError:
                # Unknown client ID
                return json_response(dict(
                    exception=UnknownClientError.__name__,
                    subcode=UnknownClientError.subcode,
                    message=UnknownClientError.message,
                    id=kwargs['client_id'],
                ), UnknownClientError.code)

        # Check that the user allowed the client
        if not UserClient.query.filter_by(
                user_id=user.id, client_id=kwargs['client_id']).count():
            # Redirect users to consent page if the client was not confirmed yet
            try:
                return redirect(
                    oauth_clients[kwargs['client_id']].consent_uri + '?' +
                    urlencode(dict(
                        client_id=kwargs['client_id'], user_id=user.id,
                        next=request.url)))
            except KeyError:
                return json_response(dict(
                    exception=UnknownClientError.__name__,
                    subcode=UnknownClientError.subcode,
                    message=UnknownClientError.message,
                    id=kwargs['client_id'],
                ), UnknownClientError.code)

        return True

    # noinspection PyUnusedLocal
    @app.route(url_prefix + 'oauth2/token', methods=['POST'])
    @oauth.token_handler
    def oauth2_token(*args, **kwargs):
        return None

    @app.route(url_prefix + 'oauth2/clients')
    @auth_required('user')
    def oauth2_clients(client_id=None):
        if client_id is None:
            return json_response(
                [dict(
                    name=client.name, id=client_id,
                    redirect_uri=client.default_redirect_uri)
                 for client_id, client in oauth_clients.items()])

        try:
            client = oauth_clients[client_id]
        except KeyError:
            raise UnknownClientError(id=client_id)
        else:
            return json_response(dict(
                name=client.name, id=client.client_id,
                redirect_uri=client.default_redirect_uri))

    @app.route(url_prefix + 'oauth2/user-clients', methods=['GET', 'POST'])
    @auth_required('user')
    def oauth2_user_clients():
        if request.method == 'GET':
            return json_response(
                [c.client_id for c in UserClient.query.filter_by(
                    user_id=current_user.id)])

        # Add client_id for the user to the db
        try:
            client_id = request.args['client_id']
        except KeyError:
            raise MissingClientIdError()

        if client_id not in oauth_clients:
            raise UnknownClientError(id=client_id)
        if not UserClient.query.filter_by(
                user_id=current_user.id, client_id=client_id).count():
            try:
                db.session.add(UserClient(
                    user_id=current_user.id, client_id=client_id))
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
            return json_response('', 201)
        return json_response()

    @app.route(url_prefix + 'oauth2/user-clients/<client_id>',
               methods=['DELETE'])
    @auth_required('user')
    def oauth2_user_clients_delete(client_id):
        if UserClient.query.filter_by(
                user_id=current_user.id, client_id=client_id).count():
            try:
                UserClient.query.filter_by(
                    user_id=current_user.id, client_id=client_id).delete()
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
        return json_response()

    app.logger.info('Initialized Afterglow OAuth2 Service')
