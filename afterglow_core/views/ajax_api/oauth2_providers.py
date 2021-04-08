"""
Afterglow Core: settings routes
"""

import secrets
import json

from flask import Response, request, redirect
from marshmallow.fields import Integer, String

from ...auth import oauth_plugins

from ... import app, json_response
from ...auth import auth_required, set_access_cookies
from ...resources.users import DbPersistentToken, db, DbUser, DbIdentity, DbRole
from ...schemas import Resource
from ...errors import ValidationError, MissingFieldError
from ...errors.auth import (
    HttpAuthFailedError, UnknownTokenError, NotInitializedError, UnknownAuthMethodError,
    NotAuthenticatedError, InitPageNotAvailableError)

from . import url_prefix


@app.route(url_prefix + '/oauth2/providers', methods=['GET'])
def oauth2_providers() -> Response:
    """
    Return available OAuth2 plugins

    :return:
        GET /ajax/oauth2/providers: list of OAuth2 plugins
    """

    plugins = [dict(id=p.id, icon=p.icon, description=p.description,
                    authorizeUrl=p.authorize_url, client_id=p.client_id, request_token_params=p.request_token_params) for p in oauth_plugins.values()]

    return json_response(plugins)

@app.route(url_prefix + '/oauth2/providers/<string:plugin_id>/authorized')
def oauth2_authorized(plugin_id: str) -> Response:
    """
    OAuth2.0 authorization code granted redirect endpoint

    :param plugin_id: OAuth2 plugin ID

    :return: redirect to original request URL
    """
    # Do not allow login if Afterglow Core has not yet been configured
    if DbUser.query.count() == 0:
        raise NotInitializedError()

    if not plugin_id or plugin_id not in oauth_plugins.keys():
        raise UnknownAuthMethodError(method=plugin_id)

    oauth_plugin = oauth_plugins[plugin_id]

    if not request.args.get('code'):
        raise MissingFieldError('code')

    if not request.args.get('redirect_uri'):
        raise MissingFieldError('redirect_uri')

    redirect_uri = request.args.get('redirect_uri')

    token = oauth_plugin.get_token(request.args.get('code'), redirect_uri)
    user_profile = oauth_plugin.get_user(token)

    if not user_profile:
        raise NotAuthenticatedError(error_msg='No user profile data returned')

    # Get the user from db
    identity = DbIdentity.query \
        .filter_by(auth_method=oauth_plugin.name, name=user_profile['id']) \
        .one_or_none()
    if identity is None and oauth_plugin.name == 'skynet':
        # A workaround for migrating the accounts of users registered in early
        # versions that used Skynet usernames instead of IDs; a potential
        # security issue is a Skynet user with a numeric username matching
        # some other user's Skynet user ID
        identity = DbIdentity.query \
            .filter_by(auth_method=oauth_plugin.name,
                       name=user_profile['username']) \
            .one_or_none()
        if identity is not None:
            # First login via Skynet after migration: replace Identity.name =
            # username with user ID to prevent a possible future account seizure
            try:
                identity.name = user_profile['id']
                identity.data = user_profile
                identity.user.first_name = \
                    user_profile.get('first_name') or None
                identity.user.last_name = user_profile.get('last_name') or None
                identity.user.email = user_profile.get('email') or None
                identity.user.birth_date = \
                    user_profile.get('birth_date') or None
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
    if identity is None:
        # Authenticated but not in the db; register a new Afterglow user if
        # allowed by plugin or the global config option
        register_users = oauth_plugin.register_users
        if register_users is None:
            register_users = app.config.get(
                'REGISTER_AUTHENTICATED_USERS', True)
        if not register_users:
            raise NotAuthenticatedError(
                error_msg='Automatic user registration disabled')

        try:
            # By default, Afterglow username becomes the same as the OAuth
            # provider username; if empty or such user already exists, also try
            # email, full name, and id
            username = None
            for username_candidate in (
                    user_profile.get('username'),
                    user_profile.get('email'),
                    ' '.join(
                        ([user_profile['first_name']]
                         if user_profile.get('first_name') else []) +
                        ([user_profile['last_name']]
                         if user_profile.get('last_name') else [])),
                    user_profile['id']):
                if username_candidate and str(username_candidate).strip() and \
                        not DbUser.query.filter(
                            db.func.lower(DbUser.username) ==
                            username_candidate.lower()).count():
                    username = username_candidate
                    break
            user = DbUser(
                username=username or None,
                first_name=user_profile.get('first_name') or None,
                last_name=user_profile.get('last_name') or None,
                email=user_profile.get('email') or None,
                birth_date=user_profile.get('birth_date') or None,
                roles=[DbRole.query.filter_by(name='user').one()],
            )
            db.session.add(user)
            db.session.flush()
            identity = DbIdentity(
                user_id=user.id,
                name=user_profile['id'],
                auth_method=oauth_plugin.name,
                data=user_profile,
            )
            db.session.add(identity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    else:
        user = identity.user
        if identity.data != user_profile:
            # Account data (e.g. API access token) has changed since the last
            # login, update it
            try:
                identity.data = user_profile
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    request.user = user
    return set_access_cookies(json_response())


