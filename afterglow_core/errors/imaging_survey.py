"""
Afterglow Core: imaging survey errors (subcodes 31xx)
"""

from . import AfterglowError


class UnknownSurveyError(AfterglowError):
    """
    SkyView does not host the given survey

    Extra attributes::
        survey: survey name
    """
    code = 404
    subcode = 3100
    message = 'SkyView does not host the given survey'


class SkyViewQueryError(AfterglowError):
    """
    An error occurred during SkyView server query

    Extra attributes::
        msg: query error message
    """
    code = 502
    subcode = 3101
    message = 'SkyView query error'


class NoSurveyDataError(AfterglowError):
    """
    Survey does not have any data for the given coordinates

    Extra attributes::
        survey: survey name
        position: coordinates or object name
    """
    code = 404
    subcode = 3102
    message = 'No data at the given coordinates'


__all__ = [name for name, value in __dict__.items()
           if issubclass(value, AfterglowError)]
