"""
Afterglow Core: data provider plugin data model

A data provider plugin must subclass :class:`DataProvider`.
"""

from typing import Any, Dict as TDict, List as TList, Optional

from marshmallow.fields import Dict, Integer, List, String

from .. import app, errors
from ..schemas import AfterglowSchema, Boolean


__all__ = ['DataProvider', 'DataProviderAsset']


class DataProviderAsset(AfterglowSchema):
    """
    Class representing a data provider asset

    Attributes::
        name: asset name (e.g. filename)
        collection: True for a collection asset
        path: asset path in the provider-specific form; serves as a unique ID
            of the asset
        metadata: extra asset metadata (e.g. data format, image dimensions,
            etc.)
    """
    name: str = String(default=None)
    collection: bool = Boolean(default=False)
    path: str = String(default=None)
    metadata: TDict[str, Any] = Dict(default={})


class DataProvider(AfterglowSchema):
    """
    Base class for data provider plugins

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

    Attributes:
        id: unique integer ID of the data provider; assigned automatically on
            initialization
        name: unique data provider name; can be used by the clients in requests
            like GET /data-providers/[id]/assets in place of the integer
            data provider ID
        auth_methods: list of data provider-specific authentication methods;
            if None, defaults to DEFAULT_DATA_PROVIDER_AUTH -> DATA_FILE_AUTH ->
            all auth methods available
        icon: optional data provider icon name
        display_name: data provider plugin visible in the Afterglow UI
        description: a longer description of the data provider
        columns: list of dictionary
            {name: string, field_name: string, sortable: boolean}
        sort_by: string - name of column to use for initial sort
        sort_asc: boolean - initial sort order should be ascending
        browseable: True if the data provider supports browsing (i.e. getting
            child assets of a collection asset at the given path); automatically
            set depending on whether the provider implements get_child_assets()
        searchable: True if the data provider supports searching (i.e. querying
            using the custom search keywords defined by `search_fields`);
            automatically set depending on whether the provider implements
            find_assets()
        search_fields: dictionary
            {field_name: {"label": label, "type": type, ...}, ...}
            containing names and descriptions of search fields used on the
            client side to create search forms
        readonly: True if the data provider assets cannot be modified (created,
            updated, or deleted); automatically set depending on whether the
            provider implements create_asset(), update_asset(), or
            delete_asset()
        quota: data provider storage quota, in bytes, if applicable
        usage: current usage of the data provider storage, in bytes, if
            applicable
    """
    __polymorphic_on__ = 'name'

    id: int = Integer(default=None)
    name: str = String(default=None)
    auth_methods: Optional[TList[str]] = List(String(), default=None)
    display_name: str = String(default=None)
    icon: str = String(default=None)
    description: str = String(default=None)
    columns: TList[TDict[str, Any]] = List(Dict(), default=[])
    sort_by: str = String(default=None)
    sort_asc: bool = Boolean(default=True)
    browseable: bool = Boolean(default=False)
    searchable: bool = Boolean(default=False)
    search_fields: TDict[str, TDict[str, Any]] = Dict(default={})
    readonly: bool = Boolean(default=True)
    quota: int = Integer(default=None)
    usage: int = Integer(default=None)

    def __init__(self, **kwargs):
        """
        Create a DataProvider instance

        :param kwargs: data provider initialization parameters
        """
        super(DataProvider, self).__init__(_set_defaults=True, **kwargs)

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
        if isinstance(self.auth_methods, str):
            self.auth_methods = self.auth_methods.split(',')

    def get_asset(self, path: str) -> DataProviderAsset:
        """
        Return an asset at the given path

        :param path: asset path

        :return: asset object
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_assets')

    def get_child_assets(self, path: str) -> TList[DataProviderAsset]:
        """
        Return child assets of a collection asset at the given path

        :param path: asset path; must identify a collection asset

        :return: list of :class:`DataProviderAsset` objects for child assets
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_child_assets')

    def find_assets(self, path: Optional[str] = None, **kwargs) \
            -> TList[DataProviderAsset]:
        """
        Return a list of assets matching the given parameters

        :param path: optional path to the collection asset to search in;
            by default (and for providers that do not have collection assets),
            search in the data provider root
        :param kwargs: provider-specific keyword=value pairs defining the
            asset(s), like name, image type or dimensions

        :return: list of :class:`DataProviderAsset` objects for assets matching
            the search query parameters
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='find_assets')

    def get_asset_data(self, path: str) -> bytes:
        """
        Return data for a non-collection asset at the given path

        :param path: asset path; must identify a non-collection asset

        :return: asset data
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_asset_data')

    def create_asset(self, path: str, data: Optional[bytes] = None, **kwargs) \
            -> DataProviderAsset:
        """
        Create an asset at the given path

        :param path: path at which to create the asset
        :param data: FITS image data; if omitted, create a collection
            asset
        :param kwargs: optional extra provider specific parameters

        :return: new data provider asset object
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='create_asset')

    def rename_asset(self, path: str, name: str) -> DataProviderAsset:
        """
        Rename asset at the given path

        :param path: path at which to create the asset
        :param name: new asset name

        :return: updated data provider asset object
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='rename_asset')

    def update_asset(self, path: str, data: bytes, **kwargs) \
            -> DataProviderAsset:
        """
        Update an asset at the given path

        :param path: path of the asset to update
        :param data: asset data; create collection asset if empty
        :param kwargs: optional extra provider-specific parameters

        :return: updated data provider asset object
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='update_asset')

    def delete_asset(self, path: str, **kwargs) -> None:
        """
        Delete an asset at the given path; recursively delete non-collection
        assets

        :param path: path of the asset to delete
        :param kwargs: optional extra provider-specific parameters
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='delete_asset')
