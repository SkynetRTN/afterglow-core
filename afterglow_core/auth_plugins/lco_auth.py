"""
Afterglow Core: Las Cumbres Observatory authentication plugin
"""

import requests

from . import HttpAuthPluginBase


class LCOAuthPlugin(HttpAuthPluginBase):
    """
    LCO HTTP auth plugin
    """
    name = 'lco'
    description = 'Login via Las Cumbres Observatory'

    def get_user(self, username: str, password: str) -> dict:
        """
        Return user profile given username and password

        :param username: username
        :param password: password

        :return: user profile
        """
        user = requests.post(
            'https://observe.lco.global/api/profile/',
            {'username': username, 'password': password}).json()
        pf = dict(
            id=username,
            api_token=user['tokens']['api_token'],
        )
        if user.get('first_name'):
            pf['first_name'] = user['first_name']
        if user.get('last_name'):
            pf['last_name'] = user['last_name']
        if user.get('email'):
            pf['email'] = user['email']
        return pf
