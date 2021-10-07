"""
Afterglow Core: data provider errors (subcodes 10xx)
"""

from . import AfterglowError


__all__ = [
    'AssetAlreadyExistsError', 'AssetNotFoundError',
    'CannotDeleteNonEmptyCollectionAssetError',
    'CannotSearchInNonCollectionError', 'CannotUpdateCollectionAssetError',
    'NonBrowseableDataProviderError', 'NonSearchableDataProviderError',
    'QuotaExceededError', 'ReadOnlyDataProviderError',
    'UnknownDataProviderError', 'UploadNotAllowedError',
]


class UnknownDataProviderError(AfterglowError):
    """
    The user requested an unknown data provider

    Extra attributes::
        id: data provider ID requested
    """
    code = 404
    subcode = 1000
    message = 'Unknown data provider ID'


class ReadOnlyDataProviderError(AfterglowError):
    """
    The user requested a POST, PUT, or DELETE for an asset of a read-only
    data provider

    Extra attributes::
        id: data provider ID requested
    """
    code = 403
    subcode = 1001
    message = 'Read-only data provider'


class NonBrowseableDataProviderError(AfterglowError):
    """
    The user requested a GET for a collection asset of a non-browseable data
    provider

    Extra attributes::
        id: data provider ID requested
    """
    code = 403
    subcode = 1002
    message = 'Non-browseable data provider'


class NonSearchableDataProviderError(AfterglowError):
    """
    The user requested a GET with search keywords for an asset of
    a non-searchable data provider

    Extra attributes::
        id: data provider ID requested
    """
    code = 403
    subcode = 1003
    message = 'Non-searchable data provider'


class AssetNotFoundError(AfterglowError):
    """
    No asset found at the given path

    Extra attributes::
        path: requested asset path
        reason: optional extra error info
    """
    code = 404
    subcode = 1004
    message = 'No asset found at the given path'


class AssetAlreadyExistsError(AfterglowError):
    """
    Attempt to create asset over the existing path

    Extra attributes::
        None
    """
    code = 409
    subcode = 1005
    message = 'Asset already exists at the given path'


class CannotSearchInNonCollectionError(AfterglowError):
    """
    Attempt to search within a path that identifies a non-collection resource

    Extra attributes::
        None
    """
    code = 403
    subcode = 1006
    message = 'Can only search in collection assets'


class CannotUpdateCollectionAssetError(AfterglowError):
    """
    Attempt to update a collection asset

    Extra attributes::
        None
    """
    code = 403
    subcode = 1007
    message = 'Cannot update a collection asset'


class CannotDeleteNonEmptyCollectionAssetError(AfterglowError):
    """
    Attempt to delete a non-empty collection asset

    Extra attributes::
        None
    """
    code = 403
    subcode = 1008
    message = 'Cannot delete non-empty collection asset without "force"'


class QuotaExceededError(AfterglowError):
    """
    Attempting to create/update an asset of a read-write data provider would
    exceed the user quota

    Extra attributes::
        quota: storage quota in bytes
        usage: used storage
        size: size of asset being created or updated
    """
    code = 403
    subcode = 1009
    message = 'Storage quota exceeded'


class UploadNotAllowedError(AfterglowError):
    """
    Attempting to upload a user file to read-write data provider that does not
    allow uploading

    Extra attributes::
        None
    """
    code = 403
    subcode = 1010
    message = 'Upload not allowed'
