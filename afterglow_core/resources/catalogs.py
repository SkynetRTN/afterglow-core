"""
Afterglow Core: catalog resource
"""

from .. import plugins
from ..models import Catalog


__all__ = ['catalogs']


# Load catalog plugins
catalogs = plugins.load_plugins(
    'catalog', 'resources.catalog_plugins', Catalog)
