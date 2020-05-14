"""
Afterglow Core: OAuth2 server errors (subcodes 2xx)
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
    subcode = 200
    message = 'Unknown OAuth2 client ID'


class MissingClientIdError(AfterglowError):
    """
    POSTing to /oauth/user-clients with no client_id

    Extra attributes::
        None
    """
    code = 400
    subcode = 201
    message = 'Missing client ID'

class UnknownTokenError(AfterglowError):
    """
    DELETEing /users/tokens/<id> with invalid id

    Extra attributes::
        None
    """
    code = 400
    subcode = 202
    message = 'Unknown token error'
