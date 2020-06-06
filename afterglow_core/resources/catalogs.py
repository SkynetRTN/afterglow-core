"""
Afterglow Core: catalog endpoint
"""

from .. import plugins
from . import catalog_plugins


__all__ = ['catalogs']


# Load catalog plugins
catalogs = plugins.load_plugins(
    'catalog', 'resources.catalog_plugins', catalog_plugins.Catalog)
