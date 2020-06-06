"""
Afterglow Core: photometric calibration errors (subcodes 40xx)
"""

from . import AfterglowError


__all__ = [
    'DuplicateFieldCalError', 'UnknownFieldCalError',
]


class UnknownFieldCalError(AfterglowError):
    """
    Unknown field calibration

    Extra attributes::
        id: requested field cal ID
    """
    code = 404
    subcode = 4000
    message = 'Unknown field cal'


class DuplicateFieldCalError(AfterglowError):
    """
    Field cal with this name already exists

    Extra attributes::
        name: field cal name
    """
    subcode = 4001
    message = 'Duplicate field cal name'
