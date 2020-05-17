"""
Afterglow Core: OAuth2 server routes
"""

from __future__ import absolute_import, division, print_function

import json

from flask import redirect, request, url_for, render_template
from .. import app, json_response
from ..users import Identity, Role, User, db
from ..errors import MissingFieldError, ValidationError
from ..errors.auth import (
    NotAuthenticatedError, NotInitializedError, UnknownAuthMethodError)
from ..errors.oauth2 import UnknownClientError
from ..auth import (
    auth_required, oauth_plugins, set_access_cookies)
from ..oauth2 import oauth_clients, oauth_server
from ..users import UserClient


@app.route('/oauth2/authorize')
@auth_required(allow_redirect=True)
def oauth2_authorize():
    client_id = request.args.get('client_id')
    if not client_id:
        raise MissingFieldError('client_id')

    # Check that the user allowed the client
    if not UserClient.query.filter_by(
            user_id=request.user.id, client_id=client_id).count():
        # Redirect users to consent page if the client was not confirmed yet
        return redirect(url_for(
            'oauth2_consent', client_id=client_id, next=request.url))

    return oauth_server.create_authorization_response(grant_user=request.user)


@app.route('/oauth2/token', methods=['POST'])
def oauth2_token():
    return oauth_server.create_token_response()


@app.route('/oauth2/<string:plugin_id>')
def oauth2_authorized(plugin_id):
    """
    OAuth2.0 authorization code granted redirect endpoint

    :return: redirect to original request URL
    :rtype: flask.Response
    """
    # Do not allow login if Afterglow Core has not yet been configured
    if User.query.count() == 0:
        raise NotInitializedError()

    state = request.args.get('state')
    if not state:
        # TODO: render error page
        raise MissingFieldError('state')

    try:
        state = json.loads(state)
    except json.JSONDecodeError:
        # TODO:  render error page
        raise ValidationError('state')

    if not plugin_id or plugin_id not in oauth_plugins.keys():
        # TODO: render error page
        raise UnknownAuthMethodError(method=plugin_id)

    oauth_plugin = oauth_plugins[plugin_id]

    if not request.args.get('code'):
        # TODO: render error page
        raise MissingFieldError('code')

    token = oauth_plugin.get_token(request.args.get('code'))
    user_profile = oauth_plugin.get_user(token)

    if not user_profile:
        raise NotAuthenticatedError(error_msg='No user profile data returned')

    # Get the user from db
    identity = Identity.query\
        .filter_by(auth_method=oauth_plugin.name, name=user_profile.id) \
        .one_or_none()
    if identity is None and oauth_plugin.name == 'skynet':
        # A workaround for migrating the accounts of users registered in early
        # versions that used Skynet usernames instead of IDs; a potential
        # security issue is a Skynet user with a numeric username matching
        # some other user's Skynet user ID
        identity = Identity.query \
            .filter_by(auth_method=oauth_plugin.name,
                       name=user_profile.username) \
            .one_or_none()
        if identity is not None:
            # First login via Skynet after migration: replace Identity.name =
            # username with user ID to prevent a possible future account seizure
            try:
                identity.name = user_profile.id
                identity.data = user_profile.json()
                identity.user.first_name = user_profile.first_name or None
                identity.user.last_name = user_profile.last_name or None
                identity.user.email = user_profile.email or None
                identity.user.birth_date = user_profile.birth_date
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
                    user_profile.username,
                    user_profile.email,
                    user_profile.full_name,
                    user_profile.id):
                if username_candidate and str(username_candidate).strip() and \
                        not User.query.filter(
                            db.func.lower(User.username) ==
                            username_candidate.lower()).count():
                    username = username_candidate
                    break
            user = User(
                username=username or None,
                first_name=user_profile.first_name or None,
                last_name=user_profile.last_name or None,
                email=user_profile.email or None,
                birth_date=user_profile.birth_date,
                roles=[Role.query.filter_by(name='user').one()],
            )
            db.session.add(user)
            db.session.flush()
            identity = Identity(
                user_id=user.id,
                name=user_profile.id,
                auth_method=oauth_plugin.name,
                data=user_profile.json(),
            )
            db.session.add(identity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    else:
        user = identity.user

    next_url = state.get('next')
    if not next_url:
        next_url = '/'
    request.user = user
    return set_access_cookies(redirect(next_url))


@app.route('/oauth2/consent', methods=['GET', 'POST'])
@auth_required(allow_redirect=True)
def oauth2_consent():
    client_id = request.args.get('client_id')
    if not client_id:
        raise MissingFieldError('client_id')

    if client_id not in oauth_clients:
        raise UnknownClientError(id=client_id)

    client = oauth_clients[client_id]

    if request.method == 'GET':
        return render_template(
            'users/consent.html.j2', oauth_client=client,
            next_url=request.args.get('next'))

    try:
        uc = UserClient()
        uc.client_id = client.client_id
        uc.user_id = request.user.id
        db.session.add(uc)
        db.session.flush()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    else:
        return json_response('', 201)
