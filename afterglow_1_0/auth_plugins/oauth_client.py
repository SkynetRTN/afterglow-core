"""
Afterglow Access Server: OAuth 1/2 authentication plugins (client-side flow)

The client must provide the final redirect URI in the "redirect" request
parameter supplied to auth/login.
"""

from __future__ import absolute_import, division, print_function

import sys
import base64
import json

from flask import abort, redirect, request, session, url_for
from authlib.integrations.flask_client import OAuth

from .. import app, auth, errors, url_prefix
from . import AuthPlugin


__all__ = ['ClientOAuthPlugin', 'GoogleClientOAuthPlugin']


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


class ClientOAuthPlugin(AuthPlugin):
    """
    Base class for OAuth plugins (client-side flow)
    """
    remote_app = None  # OAuth remote app

    def __init__(self, id=None, description=None, register_users=None,
                 **kwargs):
        """
        Initialize OAuth plugin

        :param str id: plugin ID
        :param str description: plugin description
        :param bool register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param kwargs: extra keyword arguments to :func:`OAuth.register`
        """
        super(ClientOAuthPlugin, self).__init__(
            id=id, description=description, register_users=register_users)

        self.remote_app = OAuth(app).register(
            id,
            fetch_token=lambda *_, **__:
            session.get('{}_token'.format(self.id)),
            **kwargs)

        # Register callback handler
        @app.route(url_prefix + 'auth/{}/authorized'.format(self.id),
                   endpoint='{}_authorized'.format(self.id))
        def authorized():
            orig_url = request.args.get('state', url_for('login'))

            # Disable server certificate validation in debug mode
            resp = self.remote_app.authorize_access_token(
                verify=False if app.config.get('DEBUG') else None,
            )
            if resp is None:
                # Access denied by user, return to the original url
                return redirect(orig_url)

            # Save token for communicating with remote app
            try:
                # OAuth1
                token = (resp['oauth_token'], resp['oauth_token_secret'])
            except KeyError:
                # OAuth2
                token = (resp.get('access_token'), '')
                if token[0] is None:
                    # Access denied by user
                    return redirect(orig_url)
            session['{}_token'.format(self.id)] = token

            # Retrieve the authorized user's username and save it
            session['{}_username'.format(self.id)] = self.callback(resp)

            # Redirect to the original request URL
            return redirect(orig_url)

    def get_user(self):
        """
        Return the username of the authenticated user; raise
        :class:`NoAuthError` or :class:`AuthFailedError` if the user is not
        authenticated

        :return: authenticated user's username
        :rtype: str
        """
        token_name = '{}_token'.format(self.id)
        if token_name in session and session[token_name] is None:
            # Authorization attempted but failed
            raise auth.NotAuthenticatedError()

        username_name = '{}_username'.format(self.id)
        if username_name in session:
            # Authentication finished
            username = session[username_name]
            if username is None:
                # Attempted but not authorized
                raise auth.NotAuthenticatedError()

            # Authenticated successfully
            return username

        if request.args.get('redirect'):
            # Explicit redirect passed
            target_url = request.args['redirect']
        else:
            # By default, end up in the original request URL
            target_url = request.url

        # Tell the caller to redirect to the authorization URL immediately;
        # pass the target redirect URL as state
        abort(self.remote_app.authorize_redirect(
            url_for('{}_authorized'.format(self.id), _external=True),
            state=target_url))

    def callback(self, resp):
        """
        Provider-specific authorize handler; implemented by OAuth plugin that
        retrieves the user's username using the provider API; if not authorized,
        must return None

        :param dict resp: result of calling
            :func:`authlib.client.OAuthRemoteApp.authorized_response`

        :return: username of the authorized user
        :rtype: str
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='authorized')

    def logout(self):
        """
        Delete user data from session

        :return: None
        """
        session.pop('{}_token'.format(self.id), None)
        session.pop('{}_username'.format(self.id), None)


class GoogleClientOAuthPlugin(ClientOAuthPlugin):
    """
    Google OAuth2 plugin (client-side flow)
    """
    name = 'google_client_oauth'
    type = 'oauth2client'

    def __init__(self, id=None, description='Login via Google (client-side)',
                 register_users=False, client_id=None, client_secret=None,
                 request_token_params=None):
        """
        Initialize Google OAuth2 plugin

        :param str id: plugin ID
        :param str description: plugin description
        :param bool register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param str client_id: client ID
        :param str client_secret: client secret
        :param dict request_token_params: additional token exchange parameters;
            Google requires at least scope="email", access_type="offline",
            response_type="code", which is the default
        """
        super(GoogleClientOAuthPlugin, self).__init__(
            id, description=description, register_users=register_users,
            base_url='https://www.googleapis.com/oauth2/v1/',
            access_token_url='https://accounts.google.com/o/oauth2/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            client_id=client_id, client_secret=client_secret,
            request_token_params=request_token_params if request_token_params
            else {
                'scope': 'email', 'access_type': 'offline',
                'response_type': 'code'})

    def callback(self, resp):
        """
        Google authorize handler; returns the user's Google email address as the
        Afterglow username

        :param dict resp: result of calling
            :func:`authlib.client.OAuthRemoteApp.authorized_response`

        :return: username of the authorized user
        :rtype: str
        """
        # Decode the access token (which is a JWT) and extract the email
        s = resp['access_token']
        s = s[:s.rfind('.')]
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
        # Available items: family_name, name, picture, gender, email, link,
        # given_name, id, verified_email
        user = self.remote_app.get('userinfo')
        return user.data['email']
