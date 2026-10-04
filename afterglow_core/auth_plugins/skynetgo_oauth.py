"""
Afterglow Core: Skynet Global Observatory (skynetgo.org) OAuth2 / OIDC
authentication plugin
"""

from typing import Optional

import requests
from flask import current_app

from ..errors.auth import NotAuthenticatedError
from . import OAuthServerPluginBase, OAuthToken


__all__ = ['SkynetGOOAuthPlugin', 'profile_from_claims']


class SkynetGOOAuthPlugin(OAuthServerPluginBase):
    """
    Sign in with a Skynet Global Observatory (skynetgo.org) account

    Standard OAuth2 authorization-code flow against the SkynetGO OIDC
    provider. The dashboard sends the browser to ``authorize_url``
    (auth.skynetgo.org) with ``response_type=code`` and the ``scope`` below;
    the code comes back to the dashboard's ``/oauth2/authorized`` route, and
    the base class exchanges it at ``access_token_url`` (api.skynetgo.org) as
    a *confidential* client: ``client_id`` + ``client_secret`` in the form
    body, no PKCE. :meth:`get_user` then reads the OIDC userinfo endpoint and
    maps its standard claims onto the Afterglow profile dict.

    Configuration -- one ``AUTH_PLUGINS`` entry::

        AUTH_PLUGINS = [
            {'name': 'skynetgo',
             'client_id': 'afterglow-legacy',
             'client_secret': '<secret on the SkynetGO oauth_clients row>'},
        ]

    Everything else has a working default for the production SkynetGO
    deployment. The redirect URI the dashboard sends
    (``<dashboard origin>/oauth2/authorized``) must be registered on that
    client row; SkynetGO rejects any other.

    Identity is keyed on the OIDC ``sub`` claim (the SkynetGO user's stable
    UID), so username changes on skynetgo.org do not create a second Afterglow
    user. Afterglow's own account linking still applies: a first login whose
    email matches an existing Afterglow user attaches to that user.

    Unlike :class:`SkynetOAuthPlugin`, this login does not yield a Skynet 1
    API token, so the legacy Skynet data provider is not available for these
    users; uploads and the local/sample providers work as usual.
    """
    name = 'skynetgo'

    userinfo_url = None

    def __init__(self,
                 description: Optional[str] =
                 'Login via Skynet Global Observatory',
                 icon: Optional[str] = 'skynetgo_btn_icon.png',
                 register_users: Optional[bool] = None,
                 authorize_url: str = 'https://auth.skynetgo.org/authorize',
                 access_token_url: str =
                 'https://api.skynetgo.org/oauth2/token',
                 userinfo_url: str =
                 'https://api.skynetgo.org/oauth2/userinfo',
                 scope: str = 'openid profile email',
                 client_id: str = None, client_secret: str = None,
                 request_token_params: Optional[dict] = None):
        """
        Initialize the SkynetGO OAuth2 plugin

        :param description: plugin description (button label)
        :param icon: plugin icon ID used by the client UI
        :param register_users: automatically register authenticated users
            if missing from the local user database; overrides
            REGISTER_AUTHENTICATED_USERS
        :param authorize_url: SkynetGO authorization endpoint
        :param access_token_url: SkynetGO token endpoint
        :param userinfo_url: SkynetGO OIDC userinfo endpoint
        :param scope: scopes to request; must be within the client's
            allowed scopes on the SkynetGO side
        :param client_id: client ID
        :param client_secret: client secret
        :param request_token_params: extra authorization-request parameters;
            defaults to ``{'response_type': 'code', 'scope': scope}``
        """
        if request_token_params is None:
            # The core's own Angular sign-in page (served at /core/sign-in in
            # production) forwards only state, client_id, redirect_uri and
            # these params -- it does NOT add response_type itself, and
            # SkynetGO rejects an authorize request without one. The legacy
            # Skynet plugin carries response_type for the same reason.
            request_token_params = {'response_type': 'code', 'scope': scope}

        # Always set id=name so the plugin is addressable as "skynetgo"
        super(SkynetGOOAuthPlugin, self).__init__(
            self.name, description=description, icon=icon,
            register_users=register_users, authorize_url=authorize_url,
            access_token_url=access_token_url, client_id=client_id,
            client_secret=client_secret,
            request_token_params=request_token_params)

        self.userinfo_url = userinfo_url

    def get_user(self, token: OAuthToken) -> dict:
        """
        Return the user's profile from the SkynetGO userinfo endpoint

        :param token: provider API token object

        :return: user profile
        """
        try:
            resp = requests.get(
                self.userinfo_url,
                headers={
                    'Authorization': 'Bearer {}'.format(token.access),
                },
                timeout=30,
                verify=False if current_app.config.get('DEBUG') else True)
        except requests.RequestException as e:
            raise NotAuthenticatedError(error_msg=str(e))
        if resp.status_code != 200:
            raise NotAuthenticatedError(
                error_msg='SkynetGO userinfo returned HTTP {}: {}'.format(
                    resp.status_code, resp.text))
        try:
            claims = resp.json()
        except Exception:
            raise NotAuthenticatedError(error_msg=resp.text)

        return profile_from_claims(claims)


def profile_from_claims(claims: dict) -> dict:
    """
    Map OIDC userinfo claims onto the Afterglow user profile dict

    ``id`` is the ``sub`` claim; ``username`` is ``preferred_username``
    (falling back to ``sub``); ``first_name``/``last_name`` come from
    ``given_name``/``family_name`` when present, else from splitting ``name``
    on the first space.

    :param claims: decoded userinfo JSON

    :return: profile dict as expected by :func:`afterglow_core.auth.user_login`
    """
    sub = claims.get('sub')
    if not sub:
        raise NotAuthenticatedError(
            error_msg='SkynetGO userinfo response has no "sub" claim')

    pf = dict(
        id=str(sub),
        username=claims.get('preferred_username') or str(sub),
    )

    email = claims.get('email')
    if email:
        pf['email'] = email

    first_name = claims.get('given_name')
    last_name = claims.get('family_name')
    if not (first_name or last_name):
        full_name = (claims.get('name') or '').strip()
        if full_name:
            first_name, _, last_name = full_name.partition(' ')
    if first_name:
        pf['first_name'] = first_name.strip()
    if last_name:
        pf['last_name'] = last_name.strip()

    return pf
