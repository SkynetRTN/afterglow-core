"""
Afterglow Core: data provider plugin data model

A data provider plugin must subclass :class:`DataProvider`.
"""

from __future__ import annotations

from typing import Any, Dict as TDict, List as TList, Optional, Tuple, Union

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None
from marshmallow.fields import Dict, Integer, List, String
from flask import current_app
from flask_login import current_user

from .. import PaginationInfo, errors
from ..errors.auth import NotAuthenticatedError
from ..errors.data_provider import (
    AssetNotFoundError, NonBrowseableDataProviderError, QuotaExceededError)
from ..schemas import AfterglowSchema, Boolean


__all__ = ['DataProvider', 'DataProviderAsset']


def is_overridden(base: type, instance: Any, meth: str) -> bool:
    """
    Is the given method overridden in subclass?

    :param base: base class
    :param instance: instance of a subclass of `base`
    :param meth: method name to check

    :return: True if `meth` is overridden in `instance` class
    """
    return getattr(instance, meth).__func__ is not (
        getattr(base, meth).__func__
        if hasattr(getattr(base, meth), '__func__')
        else getattr(base, meth))


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
    name: str = String(dump_default=None)
    collection: bool = Boolean(dump_default=False)
    path: str = String(dump_default=None)
    metadata: TDict[str, Any] = Dict(dump_default={})

    @property
    def mimetype(self) -> Optional[str]:
        """Non-collection asset MIME type"""
        if self.collection:
            return None

        m = 'application/octet-stream'
        try:
            imtype = self.metadata['type']
            if imtype == 'FITS':
                m = 'image/fits'
            elif PILImage is not None:
                m = PILImage.MIME[imtype]
        except KeyError:
            pass
        return m


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
            given path; must be implemented by any browsable data provider
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
            if None, defaults to DEFAULT_DATA_PROVIDER_AUTH -> DATA_FILE_AUTH
            -> all auth methods available
        icon: optional data provider icon name
        display_name: data provider plugin visible in the Afterglow UI
        description: a longer description of the data provider
        columns: list of dictionary
            {name: string, field_name: string, sortable: boolean}
        sort_by: string - name of column to use for initial sort
        sort_asc: boolean - initial sort order should be ascending
        browseable: True if the data provider supports browsing (i.e. getting
            child assets of a collection asset at the given path);
            automatically set depending on whether the provider implements
            get_child_assets()
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
        allow_upload: if readonly=False, allow uploading user images
            to the data provider
        quota: data provider storage quota, in bytes, if applicable
        usage: current usage of the data provider storage, in bytes, if
            applicable
    """
    __polymorphic_on__ = 'name'

    id: int = Integer(dump_default=None)
    name: str = String(dump_default=None)
    auth_methods: Optional[TList[str]] = List(String(), dump_default=None)
    display_name: str = String(dump_default=None)
    icon: str = String(dump_default=None)
    description: str = String(dump_default=None)
    columns: TList[TDict[str, Any]] = List(Dict(), dump_default=[])
    sort_by: str = String(dump_default=None)
    sort_asc: bool = Boolean(dump_default=True)
    browseable: bool = Boolean(dump_default=False)
    searchable: bool = Boolean(dump_default=False)
    search_fields: TDict[str, TDict[str, Any]] = Dict(dump_default={})
    readonly: bool = Boolean(dump_default=True)
    allow_upload: bool = Boolean(dump_default=False)
    quota: int = Integer(dump_default=None)
    usage: int = Integer(dump_default=None)

    def __init__(self, **kwargs):
        """
        Create a DataProvider instance

        :param kwargs: data provider initialization parameters
        """
        super(DataProvider, self).__init__(**kwargs)

        # Automatically set browseable, searchable, and readonly flags
        # depending on what methods are reimplemented by provider; method attr
        # of a class is an unbound method instance in Python 2 and a function
        # in Python 3
        if 'browseable' not in kwargs:
            self.browseable = is_overridden(
                DataProvider, self, 'get_child_assets')
        if 'searchable' not in kwargs:
            self.searchable = is_overridden(DataProvider, self, 'find_assets')
        if 'readonly' not in kwargs:
            self.readonly = \
                not is_overridden(DataProvider, self, 'create_asset') and \
                not is_overridden(DataProvider, self, 'update_asset') and \
                not is_overridden(DataProvider, self, 'delete_asset')

        if self.auth_methods is None:
            # Use default data provider authentication
            self.auth_methods = current_app.config.get(
                'DEFAULT_DATA_PROVIDER_AUTH')
            if self.auth_methods is None:
                # Inherit auth methods from data files
                self.auth_methods = current_app.config.get('DATA_FILE_AUTH')
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

    def get_child_assets(self, path: str, sort_by: Optional[str] = None,
                         page_size: Optional[int] = None,
                         page: Optional[Union[int, str]] = None) \
            -> Tuple[TList[DataProviderAsset], Optional[PaginationInfo]]:
        """
        Return child assets of a collection asset at the given path

        :param path: asset path; must identify a collection asset
        :param sort_by: optional sorting key (e.g. column name); reverse
            sorting is indicated by prepending a hyphen to the key; data
            provider may assume a certain default sorting mode and must return
            it in the pagination info
        :param page_size: optional number of assets per page; None means don't
            use pagination (used only internally, never via the API);
            if not None, data provider may enforce a hard limit on the page
            size
        :param page: page-based pagination: optional 0-based page number (data
            provider returns at most `page_size` assets sorted by the sorting
            key at offset = `page`*`page_size`);
            keyset-based pagination: ">value" = return at most `page_size`
            assets with the value of `sort_by` key greater than the given
            value, "<value": return at most `page_size` assets with the value
            of the `sort_by` key smaller than the given value;
            for any pagination type, two special values "first" and "last"
            are used to return first and last page, respectively

        :return: list of :class:`DataProviderAsset` objects for child assets
            and pagination info or None if pagination is not supported
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='get_child_assets')

    def find_assets(self, path: Optional[str] = None,
                    sort_by: Optional[str] = None,
                    page_size: Optional[int] = None,
                    page: Optional[Union[int, str]] = None,
                    **kwargs) \
            -> Tuple[TList[DataProviderAsset], Optional[PaginationInfo]]:
        """
        Return a list of assets matching the given parameters

        :param path: optional path to the collection asset to search in;
            by default (and for providers that do not have collection assets),
            search in the data provider root
        :param sort_by: optional sorting key; see :meth:`get_child_assets`
        :param page_size: optional number of assets per page
        :param page: optional 0-based page number, ">value", "<value", "first",
            or "last"
        :param kwargs: provider-specific keyword=value pairs defining the
            asset(s), like name, image type or dimensions

        :return: list of :class:`DataProviderAsset` objects for assets matching
            the search query parameters and pagination info or None
            if pagination is not supported
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

    def rename_asset(self, path: str, name: str, **kwargs) \
            -> DataProviderAsset:
        """
        Rename asset at the given path

        :param path: path at which to create the asset
        :param name: new asset name
        :param kwargs: optional extra provider specific parameters

        :return: updated data provider asset object
        """
        raise errors.MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='rename_asset')

    def update_asset(self, path: str, data: Optional[bytes], **kwargs) \
            -> DataProviderAsset:
        """
        Update an asset at the given path

        :param path: path of the asset to update
        :param data: asset data; create collection asset if None
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

    def check_quota(self: DataProvider, path: Optional[str], data: bytes) \
            -> None:
        """
        Check that the new asset data will not exceed the data provider's quota

        :param path: asset path; must be set if updating existing asset
        :param data: asset data being saved
        """
        quota = self.quota
        if quota:
            usage = self.usage or 0
            size = len(data) if data is not None else 0
            if path is not None:
                usage -= self.get_asset(path).metadata.get('size', 0)
            if usage + size > quota:
                raise QuotaExceededError(quota=quota, usage=usage, size=size)

    def check_auth(self) -> None:
        """
        Check that the user is authenticated with any of the auth methods
        required for the data provider; raises NotAuthenticatedError if not
        """
        if not current_app.config.get('AUTH_ENABLED'):
            # User auth disabled, always succeed
            return

        auth_methods = self.auth_methods
        if not auth_methods:
            # No specific auth methods requested
            return

        # Check that any of the auth methods requested is present
        # in any of the user's identities
        for required_method in auth_methods:
            if required_method == 'http':
                # HTTP auth requires username and password being set
                if getattr(current_user, 'username', None) and \
                        getattr(current_user, 'password', None):
                    return
                continue

            # For non-HTTP methods, check identities
            try:
                for identity in getattr(current_user, 'identities', []):
                    if identity.auth_method == required_method:
                        return
            except AttributeError:
                pass

        raise NotAuthenticatedError(
            error_msg='Data provider "{}" requires authentication with either '
            'of the methods: {}'.format(self.id, ', '.join(auth_methods)))

    def recursive_copy(self, provider: DataProvider,
                       src_path: str, dst_path: str,
                       move: bool = False, update: Optional[bool] = None,
                       force: bool = False, limit: int = 0, _depth: int = 0,
                       **kwargs) \
            -> DataProviderAsset:
        """
        Copy the whole asset from another data provider or a different path
        within the same data provider

        :param provider: source data provider; can be the same as the current
            provider
        :param src_path: asset path within the source data provider
        :param dst_path: destination asset path within the current data
            provider
        :param move: delete source asset after successful copy
        :param update: update existing asset at `dst_path` vs create
            a new asset; None (default) means auto
        :param force: overwrite existing top-level collection asset if updating
        :param limit: recursion limit for the copy
        :param _depth: current recursion depth; keep as is
        :param kwargs: optional provider-specific keyword arguments to
            :meth:`create_asset`, :meth:`update_asset`, and
            :meth:`delete_asset`

        :return: new data provider asset
        """
        if update is None:
            # Create or update top-level asset?
            try:
                self.get_asset(dst_path)
            except AssetNotFoundError:
                update = False
            else:
                update = True

        src_asset = provider.get_asset(src_path)
        if src_asset.collection:
            # Copying the whole collection asset tree; first, create/update
            # empty collection asset at dst_path
            if not provider.browseable:
                raise NonBrowseableDataProviderError(id=provider.id)
            if update:
                res = self.update_asset(dst_path, None, force=force, **kwargs)
            else:
                res = self.create_asset(dst_path, None, **kwargs)

            if not limit or _depth < limit - 1:
                for child_asset in provider.get_child_assets(src_path)[0]:
                    # For each child asset of a collection asset, recursively
                    # copy its data; calculate the destination path by
                    # appending the source asset name; always create
                    # destination asset since no asset exists there yet
                    self.recursive_copy(
                        provider, child_asset.path,
                        dst_path + '/' + child_asset.name, move=move,
                        update=False, limit=limit, _depth=_depth + 1, **kwargs)
        else:
            # Copying a non-collection asset
            src_data = provider.get_asset_data(src_path)
            self.check_quota(dst_path if update else None, src_data)
            if update:
                # Updating top-level destination asset
                res = self.update_asset(
                    dst_path, src_data, force=force, **kwargs)
            else:
                # Creating non-collection asset
                res = self.create_asset(dst_path, src_data, **kwargs)

        if move:
            # Delete the source asset after successful copy
            self.delete_asset(src_path, **kwargs)

        return res
