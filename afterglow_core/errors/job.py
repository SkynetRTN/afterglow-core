"""
Afterglow Core: job errors
"""

from . import AfterglowError


__all__ = [
    'CannotCancelJobError', 'CannotCreateJobFileError', 'CannotDeleteJobError',
    'CannotSetJobStatusError', 'InvalidMethodError', 'JobServerError',
    'JobWorkerRAMExceeded', 'UnknownJobError', 'UnknownJobFileError',
    'UnknownJobTypeError',
]


class JobServerError(AfterglowError):
    """
    Unhandled job server error

    Extra attributes::
        reason: error message describing the reason of failure
    """
    code = 500
    message = 'Internal job server error'


class UnknownJobError(AfterglowError):
    """
    Unknown job ID requested

    Extra attributes::
        id: job ID
    """
    code = 404
    message = 'Unknown job'


class UnknownJobFileError(AfterglowError):
    """
    Unknown job file ID requested

    Extra attributes::
        id: job file ID
    """
    code = 404
    message = 'Unknown job file'


class UnknownJobTypeError(AfterglowError):
    """
    Creating a job which type is not registered

    Extra attributes::
        type: job type
    """
    code = 400
    message = 'Unknown job type'


class InvalidMethodError(AfterglowError):
    """
    The given resource does not support HTTP method requested

    Extra attributes::
        resource: resource ID
        method: HTTP method requested
    """
    code = 405
    message = 'Method is not supported'


class CannotSetJobStatusError(AfterglowError):
    """
    Setting job status to something other than "canceled"

    Extra attributes::
        status: job status
    """
    code = 403
    message = 'Cannot set job status'


class CannotCancelJobError(AfterglowError):
    """
    Canceling a job that is not in in_progress state

    Extra attributes::
        status: job status
    """
    code = 403
    message = 'Cannot cancel job'


class CannotDeleteJobError(AfterglowError):
    """
    Deleting a job that is not in completed or canceled state

    Extra attributes::
        status: job status
    """
    code = 403
    message = 'Cannot delete job in its current state'


class JobWorkerRAMExceeded(AfterglowError):
    """
    Current jobs use too much RAM to start one more job

    Extra attributes::
        job_worker_ram_percent: current RAM usage by all job workers (%)
    """
    code = 403
    message = 'Job worker RAM usage exceeded, try again later'


class CannotCreateJobFileError(AfterglowError):
    """
    Error creating extra job file

    Extra attributes::
        id: job file ID
        reason: error message describing the reason of failure
    """
    code = 500
    message = 'Cannot create job file'
