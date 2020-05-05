"""
Afterglow Core: data provider plugin package

A data provider plugin must subclass :class:`DataProvider` and implement at
least its get_asset() and get_asset_data() methods. Browseable data providers
must implement get_child_assets(). Searchable providers must implement
find_assets(). Finally, read-write providers, must also implement
create_asset(), update_asset(), and delete_asset().
"""

from __future__ import absolute_import, division, print_function

from ... import app
from ...errors import MethodNotImplementedError
from ...models.data_provider import DataProviderSchema
from ...auth import oauth_plugins


__all__ = ['DataProvider']


class DataProvider(DataProviderSchema):
    """
    Base class for JSON-serializable data provider plugins

    Plugin modules are placed in the :mod:`resources.data_provider_plugins`
    subpackage and must subclass from :class:`DataProvider`, e.g.

    class MyDataProvider(DataProvider):
        name = 'my_provider'
        search_fields = {...}

        def get_asset(self, path):
            ...

        def get_asset_data(self, path):
            ...

        def get_child_assets(self, path):
            ...

        def find_assets(self, path=None, **kwargs):
            ...

    Methods:
        get_asset(): return asset at the given path; must be implemented by any
            data provider
        get_asset_data(): return data for a non-collection asset at the given
            path; must be implemented by any data provider
        get_child_assets(): return child assets of a collection asset at the
            given path; must be implemented by any browseable data provider
        find_assets(): return assets matching the given parameters; must be
            implemented by any searchable data provider
        create_asset(): create a new non-collection asset from data file at the
            given path, or an empty collection asset at the given path; must be
            implemented by a read-write provider if it supports adding new
            assets
        update_asset(): update an existing non-collection asset at the given
            path with a data file; must be implemented by a read-write provider
            if it supports modifying existing assets
        delete_asset(): delete an asset at the given path; must be implemented
            by a read-write provider if it supports deleting assets
    """
    # noinspection PyUnresolvedReferences
    def __init__(self, *args, **kwargs):
        """
        Create a DataProvider instance

        :param args: see :class:`afterglow_core.Resource`
        :param kwargs: see :class:`afterglow_core.Resource`
        """
        super(DataProvider, self).__init__(*args, **kwargs)

        # Automatically set browseable, searchable, and readonly flags depending
        # on what methods are reimplemented by provider; method attr of a class
        # is an unbound method instance in Python 2 and a function in Python 3
        if 'browseable' not in kwargs:
            self.browseable = self.get_child_assets.__func__ is not \
                (DataProvider.get_child_assets.__func__
                 if hasattr(DataProvider.get_child_assets, '__func__')
                 else DataProvider.get_child_assets)
        if 'searchable' not in kwargs:
            self.searchable = self.find_assets.__func__ is not \
                (DataProvider.find_assets.__func__
                 if hasattr(DataProvider.find_assets, '__func__')
                 else DataProvider.find_assets)
        if 'readonly' not in kwargs:
            self.readonly = self.create_asset.__func__ is \
                (DataProvider.create_asset.__func__
                 if hasattr(DataProvider.create_asset, '__func__')
                 else DataProvider.create_asset) and \
                self.update_asset.__func__ is \
                (DataProvider.update_asset.__func__
                 if hasattr(DataProvider.update_asset, '__func__')
                 else DataProvider.update_asset) and \
                self.delete_asset.__func__ is \
                (DataProvider.delete_asset.__func__
                 if hasattr(DataProvider.delete_asset, '__func__')
                 else DataProvider.delete_asset)

        if self.auth_methods is None:
            # Use default data provider authentication
            self.auth_methods = app.config.get('DEFAULT_DATA_PROVIDER_AUTH')
            if self.auth_methods is None:
                # Inherit auth methods from data files
                self.auth_methods = app.config.get('DATA_FILE_AUTH')
                if self.auth_methods is None:
                    # Use all available auth methods
                    self.auth_methods = [
                        plugin.id for plugin in oauth_plugins.values()]
        if isinstance(self.auth_methods, str):
            self.auth_methods = [self.auth_methods]

    def get_asset(self, path):
        """
        Return an asset at the given path

        :param str path: asset path

        :return: asset object
        :rtype: afterglow_core.models.data_provider.DataProviderAsset
        """
        raise MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_assets')

    def get_child_assets(self, path):
        """
        Return child assets of a collection asset at the given path

        :param str path: asset path; must identify a collection asset

        :return: list of :class:`DataProviderAsset` objects for child assets
        :rtype: list[afterglow_core.models.data_provider.DataProviderAsset]
        """
        raise MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_child_assets')

    def find_assets(self, path=None, **kwargs):
        """
        Return a list of assets matching the given parameters

        :param str path: optional path to the collection asset to search in;
            by default (and for providers that do not have collection assets),
            search in the data provider root
        :param kwargs: provider-specific keyword=value pairs defining the
            asset(s), like name, image type or dimensions

        :return: list of :class:`DataProviderAsset` objects for assets matching
            the search query parameters
        :rtype: list[afterglow_core.models.data_provider.DataProviderAsset]
        """
        raise MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='find_assets')

    def get_asset_data(self, path):
        """
        Return data for a non-collection asset at the given path

        :param str path: asset path; must identify a non-collection asset

        :return: asset data
        :rtype: str
        """
        raise MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_asset_data')

    def create_asset(self, path, data=None, **kwargs):
        """
        Create an asset at the given path

        :param str path: path at which to create the asset
        :param bytes data: FITS image data; if omitted, create a collection
            asset
        :param kwargs: optional extra provider specific parameters

        :return: new data provider asset object
        :rtype: :class:`afterglow_core.models.data_provider.DataProviderAsset`
        """
        raise MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='create_asset')

    def update_asset(self, path, data, **kwargs):
        """
        Update an asset at the given path

        :param str path: path of the asset to update
        :param bytes data: FITS image data
        :param kwargs: optional extra provider-specific parameters

        :return: updated data provider asset object
        :rtype: :class:`afterglow_core.models.data_provider.DataProviderAsset`
        """
        raise MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='update_asset')

    def delete_asset(self, path, **kwargs):
        """
        Delete an asset at the given path; recursively delete non-collection
        assets

        :param str path: path of the asset to delete
        :param kwargs: optional extra provider-specific parameters

        :return: None
        """
        raise MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='delete_asset')
