"""
Afterglow Core: data-providers resource

The list of data provider plugins loaded at runtime is controlled by the
DATA_PROVIDERS configuration variable.
"""

from typing import Dict as TDict, Union

from .. import app, plugins
from ..models import DataProvider


__all__ = ['providers']


# Load data provider plugins
providers: TDict[Union[int, str], DataProvider] = plugins.load_plugins(
    'data provider', 'resources.data_provider_plugins',
    DataProvider, app.config.get('DATA_PROVIDERS', []))
