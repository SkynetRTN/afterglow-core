"""
Afterglow Core: imaging survey errors
"""

from . import AfterglowError


__all__ = [
    'NoSurveyDataError', 'SkyViewQueryError', 'UnknownSurveyError',
]


class UnknownSurveyError(AfterglowError):
    """
    SkyView does not host the given survey

    Extra attributes::
        survey: survey name
    """
    code = 404
    message = 'SkyView does not host the given survey'


class SkyViewQueryError(AfterglowError):
    """
    An error occurred during SkyView server query

    Extra attributes::
        msg: query error message
    """
    code = 502
    message = 'SkyView query error'


class NoSurveyDataError(AfterglowError):
    """
    Survey does not have any data for the given coordinates

    Extra attributes::
        survey: survey name
        position: coordinates or object name
    """
    code = 404
    message = 'No data at the given coordinates'
