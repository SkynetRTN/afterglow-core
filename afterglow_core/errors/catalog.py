"""
Afterglow Core: catalog errors (subcodes 30xx)
"""

from . import AfterglowError


class UnknownCatalogError(AfterglowError):
    """
    The user requested an unknown catalog

    Extra attributes::
        name: catalog name requested
    """
    code = 404
    subcode = 3000
    message = 'Unknown catalog'


_all__ = [name for name, value in __dict__.items()
          if issubclass(value, AfterglowError)]
