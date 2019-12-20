"""
Afterglow Access Server: error system
"""

from __future__ import absolute_import, division, print_function
import sys
import traceback
from werkzeug import exceptions
from . import app, json_response


__all__ = ['AfterglowError', 'MethodNotImplementedError', 'ValidationError']


def afterglow_error_handler(e):
    """
    Error handling function for all Afterglow Access Server errors

    Automatically installed for all `AfterglowError` subclasses via
    `AfterglowErrorMeta`

    :param Exception e: exception instance

    :return: JSON response object
    :rtype: :class:`flask.Response`
    """
    if hasattr(e, 'payload') and e.payload:
        payload = dict(e.payload)
    else:
        payload = {}
    payload['exception'] = e.__class__.__name__
    # noinspection PyUnresolvedReferences
    payload['message'] = e.message if hasattr(e, 'message') and e.message \
        else ', '.join(str(arg) for arg in e.args) if e.args else str(e)

    if hasattr(e, 'subcode') and e.subcode:
        payload['subcode'] = int(e.subcode)

    if getattr(e, 'code', 400) == 500:
        payload['traceback'] = traceback.format_tb(sys.exc_info()[-1]),

    response = json_response(
        payload, int(e.code) if hasattr(e, 'code') and e.code else 400)
    response.mimetype = 'application/json'

    if hasattr(e, 'headers') and e.headers:
        for name, val in e.headers:
            response.headers[name] = val

    return response


@app.errorhandler(401)
def unauthorized_error_handler(e):
    """
    Error handling function for HTTP 401 (UNAUTHORIZED)

    :param Exception e: exception instance

    :return: JSON response object
    :rtype: :class:`flask.Response`
    """
    # noinspection PyUnresolvedReferences
    return json_response(
        {
            'exception': e.__class__.__name__,
            'message': e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e),
        }, 401)


@app.errorhandler(403)
def forbidden_error_handler(e):
    """
    Error handling function for HTTP 403 (FORBIDDEN)

    :param Exception e: exception instance

    :return: JSON response object
    :rtype: :class:`flask.Response`
    """
    # noinspection PyUnresolvedReferences
    return json_response(
        {
            'exception': e.__class__.__name__,
            'message': e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e),
        }, 403)


@app.errorhandler(404)
def not_found_error_handler(e):
    """
    Error handling function for HTTP 404 (NOT FOUND); raised when a nonexistent
    resource is requested

    :param Exception e: exception instance

    :return: JSON response object
    :rtype: :class:`flask.Response`
    """
    # noinspection PyUnresolvedReferences
    return json_response(
        {
            'exception': e.__class__.__name__,
            'message': e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e),
        }, 404)


@app.errorhandler(500)
def internal_server_error_handler(e):
    """
    Error handling function for HTTP 500 (INTERNAL SERVER ERROR)

    :param Exception e: exception instance

    :return: JSON response object
    :rtype: :class:`flask.Response`
    """
    # noinspection PyUnresolvedReferences
    return json_response(
        {
            'exception': e.__class__.__name__,
            'message': e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e),
            'traceback': traceback.format_tb(sys.exc_info()[-1]),
        }, 500)


class AfterglowErrorMeta(type):
    """
    Metaclass for `AfterglowError`; needed to automatically install error
    handler for each exception subclassing from `AfterglowError`, since Flask
    does not intercept subclassed exceptions in the base exception class handler
    """
    def __new__(mcs, *args, **kwargs):
        c = type.__new__(mcs, *args, **kwargs)
        app.register_error_handler(c, afterglow_error_handler)
        return c


class AfterglowError(exceptions.HTTPException):
    """
    Base class for all Afterglow Access Server exceptions

    :Attributes::
        code: HTTP status code for the exception, defaults to 400 (BAD REQUEST)
        subcode: exception-specific error code; by convention, has the form
            "nmm", where the most significant digits ("n") define the Afterglow
            Access Server module and the two least significant digits ("mm")
            define specific exception within that module, from 0 to 99
        payload: dictionary containing the optional exception attributes passed
            as keyword arguments when raising the exception and sent to the
            client in JSON
        headers: any additional HTTP headers to send
    """
    __metaclass__ = AfterglowErrorMeta

    code = 400  # HTTP status code
    subcode = None  # Afterglow-specific error code
    payload = None  # additional error data

    def __init__(self, **kwargs):
        """
        Create an Afterglow exception instance

        :param kwargs: optional extra data sent to the client in the body of
            the error response; the special keyword "message" is always set to
            the error description text
        """
        super(AfterglowError, self).__init__()
        if not self.description and self.__doc__:
            self.description = self.__doc__
        self.payload = kwargs

    def __str__(self):
        """
        Return a string representation of an Afterglow error showing both error
        message and payload

        :return: stringified Afterglow error
        :rtype: str
        """
        msg = self.message
        if self.payload:
            msg += ' ({})'.format(
                ', '.join('{}={}'.format(name, val)
                          for name, val in self.payload.items()))
        return msg


class MethodNotImplementedError(AfterglowError):
    """
    Resource method is not implemented by the Afterglow Access Server. Mainly
    used by the data provider plugin system if the plugin class does not
    override the required abstract base DataProvider class method.

    Extra attributes::
        class_name: name of the class that must implement the method
        method_name: name of the method to implement
    """
    code = 501
    subcode = 1
    message = 'Method not implemented'


class ValidationError(AfterglowError):
    """
    Server-side validation fails for a certain field passed as a request
    parameter

    Extra attributes::
        field: name of the field
    """
    subcode = 2
    message = 'Validation failed'

    def __init__(self, field, message=None, code=400):
        super(ValidationError, self).__init__(field=field)
        if message:
            self.message = message
        self.code = code


class MissingFieldError(ValidationError):
    """
    Required data is missing from request parameters

    Extra attributes::
        field: name of the field
    """
    subcode = 3
    message = 'Missing required data'


class NotAcceptedError(AfterglowError):
    """
    The client requested the MIME type that the server cannot return

    Extra attributes::
        accepted_mimetypes: Accept header value sent by the client
    """
    code = 406
    subcode = 4
    message = 'Sending data in the format requested by HTTP Accept header ' \
        'is not supported'
