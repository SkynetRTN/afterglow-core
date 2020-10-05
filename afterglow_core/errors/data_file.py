"""
Afterglow Core: data file errors (subcodes 20xx)
"""

from . import AfterglowError


__all__ = [
    'CannotCreateDataFileDirError', 'CannotImportFromCollectionAssetError',
    'MissingWCSError', 'UnknownDataFileError', 'UnrecognizedDataFileError',
    'UnknownSessionError', 'DuplicateSessionNameError',
]


class UnknownDataFileError(AfterglowError):
    """
    Format of the data file being imported is not recognized

    Extra attributes::
        id: requested data file ID
    """
    code = 404
    subcode = 2000
    message = 'Unknown data file ID'


class CannotCreateDataFileDirError(AfterglowError):
    """
    Initializing the user data file storage failed (e.g. directory not
    writeable or database creation error)

    Extra attributes::
        reason: error message describing the reason why the operation has failed
    """
    code = 403
    subcode = 2001
    message = 'Cannot create data file storage directory'


class CannotImportFromCollectionAssetError(AfterglowError):
    """
    An attempt was made to import a data file from a collection asset

    Extra attributes::
        provider_id: data provider ID
        path: requested asset path
    """
    code = 403
    subcode = 2002
    message = 'Cannot import from collection asset'


class UnrecognizedDataFileError(AfterglowError):
    """
    An attempt was made to import a data file that has unknown format

    Extra attributes::
        none
    """
    code = 403
    subcode = 2003
    message = 'Data file format not recognized'


class MissingWCSError(AfterglowError):
    """
    Data file has now WCS calibration

    Extra attributes::
        none
    """
    code = 400
    subcode = 2004
    message = 'Missing WCS info'


class UnknownSessionError(AfterglowError):
    """
    Requested session with unknown ID or name

    Extra attributes::
        id: session ID or name
    """
    code = 404
    subcode = 2005
    message = 'Unknown session'


class DuplicateSessionNameError(AfterglowError):
    """
    Session with the given name already exists

    Extra attributes::
        name: session name
    """
    subcode = 2006
    message = 'Duplicate session name'
