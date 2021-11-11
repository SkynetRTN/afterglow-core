"""
Afterglow Core: catalog errors
"""

from . import AfterglowError


__all__ = [
    'UnknownCatalogError',
]


class UnknownCatalogError(AfterglowError):
    """
    The user requested an unknown catalog

    Extra attributes::
        name: catalog name requested
    """
    code = 404
    message = 'Unknown catalog'
