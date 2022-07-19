"""
Afterglow Core: data provider schemas
"""

from marshmallow.fields import Boolean, Dict, Integer, List, String

from ... import Resource


__all__ = ['DataProviderSchema', 'DataProviderAssetSchema']


class DataProviderSchema(Resource):
    """
    Data provider plugin schema

    Fields:
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
    __get_view__ = 'data_providers'

    id = Integer(dump_default=None)
    name = String(dump_default=None)
    auth_methods = List(String(), dump_default=None)
    display_name = String(dump_default=None)
    icon = String(dump_default=None)
    description = String(dump_default=None)
    columns = List(Dict(), dump_default=[])
    sort_by = String(dump_default=None)
    sort_asc = Boolean(dump_default=True)
    browseable = Boolean(dump_default=False)
    searchable = Boolean(dump_default=False)
    search_fields = Dict(dump_default={})
    readonly = Boolean(dump_default=True)
    quota = Integer(dump_default=None)
    usage = Integer(dump_default=None)


class DataProviderAssetSchema(Resource):
    """
    Class representing a JSON-serializable data provider asset

    Attributes::
        name: asset name (e.g. filename)
        collection: True for a collection asset
        path: asset path in the provider-specific form; serves as a unique ID
            of the asset
        metadata: extra asset metadata (e.g. data format, image dimensions,
            etc.)
    """
    name = String(dump_default=None)
    collection = Boolean(dump_default=False)
    path = String(dump_default=None)
    metadata = Dict(dump_default={})
