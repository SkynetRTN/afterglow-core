"""
Afterglow Core: local disk data provider errors (subcodes 11xx)
"""

from . import AfterglowError


class AssetOutsideRootError(AfterglowError):
    """
    An asset requested that is outside the root data directory
    """
    code = 404
    subcode = 1100
    message = 'Asset path outside the data directory'


class UnrecognizedDataFormatError(AfterglowError):
    """
    File at the given path has unknown format
    """
    code = 404
    subcode = 1101
    message = 'Data file format not recognized'


class FilesystemError(AfterglowError):
    """
    Attempting to do a filesystem operation on asset failed (e.g. permission
    denied)

    Extra attributes::
        reason: error message describing the reason of failure
    """
    code = 403
    subcode = 1102
    message = 'Filesystem error'


__all__ = [name for name, value in globals().items()
           if issubclass(value, AfterglowError)]
