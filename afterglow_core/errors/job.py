"""
Afterglow Core: job errors (subcodes 3xx)
"""

from . import AfterglowError


__all__ = [
    'CannotCancelJobError', 'CannotCreateJobFileError', 'CannotDeleteJobError',
    'CannotSetJobStatusError', 'InvalidMethodError', 'JobServerError',
    'UnknownJobError', 'UnknownJobFileError', 'UnknownJobTypeError',
]


class JobServerError(AfterglowError):
    """
    Unhandled job server error

    Extra attributes::
        reason: error message describing the reason of failure
    """
    code = 500
    subcode = 300
    message = 'Internal job server error'


class UnknownJobError(AfterglowError):
    """
    Unknown job ID requested

    Extra attributes::
        id: job ID
    """
    code = 404
    subcode = 301
    message = 'Unknown job'


class UnknownJobFileError(AfterglowError):
    """
    Unknown job file ID requested

    Extra attributes::
        id: job file ID
    """
    code = 404
    subcode = 302
    message = 'Unknown job file'


class UnknownJobTypeError(AfterglowError):
    """
    Creating a job which type is not registered

    Extra attributes::
        type: job type
    """
    code = 400
    subcode = 303
    message = 'Unknown job type'


class InvalidMethodError(AfterglowError):
    """
    The given resource does not support HTTP method requested

    Extra attributes::
        resource: resource ID
        method: HTTP method requested
    """
    code = 405
    subcode = 304
    message = 'Method is not supported'


class CannotSetJobStatusError(AfterglowError):
    """
    Setting job status to something other than "canceled"

    Extra attributes::
        status: job status
    """
    code = 403
    subcode = 305
    message = 'Cannot set job status'


class CannotCancelJobError(AfterglowError):
    """
    Canceling a job that is not in in_progress state

    Extra attributes::
        status: job status
    """
    code = 403
    subcode = 306
    message = 'Cannot cancel job'


class CannotDeleteJobError(AfterglowError):
    """
    Deleting a job that is not in completed or canceled state

    Extra attributes::
        status: job status
    """
    code = 403
    subcode = 307
    message = 'Cannot delete job in its current state'


class CannotCreateJobFileError(AfterglowError):
    """
    Error creating extra job file

    Extra attributes::
        id: job file ID
        reason: error message describing the reason of failure
    """
    code = 500
    subcode = 308
    message = 'Cannot create job file'
