"""
Afterglow Core: local disk data provider errors
"""

from . import AfterglowError


__all__ = [
    'AssetOutsideRootError', 'FilesystemError',
]


class AssetOutsideRootError(AfterglowError):
    """
    An asset requested that is outside the root data directory
    """
    code = 404
    message = 'Asset path outside the data directory'


class FilesystemError(AfterglowError):
    """
    Attempting to do a filesystem operation on asset failed (e.g. permission
    denied)

    Extra attributes::
        reason: error message describing the reason of failure
    """
    code = 403
    message = 'Filesystem error'
