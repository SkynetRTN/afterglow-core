"""
Afterglow Core: data-providers resource

The list of data provider plugins loaded at runtime is controlled by the
DATA_PROVIDERS configuration variable.
"""

from .. import app, plugins
from . import data_provider_plugins


__all__ = ['providers']


# Load data provider plugins
providers = plugins.load_plugins(
    'data provider', 'resources.data_provider_plugins',
    data_provider_plugins.DataProvider, app.config.get('DATA_PROVIDERS', []))
