"""
Afterglow Core: OAuth2 server errors
"""

from . import AfterglowError


__all__ = [
    'MissingClientIdError', 'UnknownClientError',
]


class UnknownClientError(AfterglowError):
    """
    The user requested an unknown OAuth2 client

    Extra attributes::
        id: client ID requested
    """
    code = 404
    message = 'Unknown OAuth2 client ID'


class MissingClientIdError(AfterglowError):
    """
    POSTing to /oauth/user-clients with no client_id

    Extra attributes::
        None
    """
    code = 400
    message = 'Missing client ID'
