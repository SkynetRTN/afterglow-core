#TODO remove unused imports
"""
Afterglow Core: catalog endpoint
"""

from __future__ import absolute_import, division, print_function

from .. import app, json_response, plugins
from ..auth import auth_required
from ..errors.catalog import UnknownCatalogError
from . import catalog_plugins


__all__ = ['catalogs']


# Load catalog plugins
catalogs = plugins.load_plugins(
    'catalog', 'resources.catalog_plugins', catalog_plugins.Catalog)
