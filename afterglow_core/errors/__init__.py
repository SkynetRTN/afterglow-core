"""
Afterglow Core: error system
"""

import sys
import json
import traceback
from typing import Optional

from flask import Flask, Response, request
from werkzeug import exceptions
from werkzeug.http import HTTP_STATUS_CODES


__all__ = [
    'AfterglowError', 'MethodNotImplementedError', 'ValidationError',
    'MissingFieldError', 'NotAcceptedError',
    'register',
]


exc_classes = {}


def register(app: Flask) -> None:
    """
    Install app error handlers

    :param app: Flask application
    """
    # Install standard HTTP error handlers
    app.register_error_handler(401, unauthorized_error_handler)
    app.register_error_handler(403, forbidden_error_handler)
    app.register_error_handler(404, not_found_error_handler)
    app.register_error_handler(500, internal_server_error_handler)

    # Install error handlers for all defined exceptions
    for c in exc_classes.values():
        app.register_error_handler(c, afterglow_error_handler)


def afterglow_error_handler(e: Exception) -> Response:
    """
    Error handling function for all Afterglow Core errors

    Automatically installed for all `AfterglowError` subclasses via
    `AfterglowErrorMeta`

    :param e: exception instance

    :return: JSON response object
    """
    status = int(getattr(e, 'code', 400))

    error = {
        'status': HTTP_STATUS_CODES.get(
            status, '{} Unknown Error'.format(status)),
        'id': str(getattr(e, 'id', e.__class__.__name__)),
        'detail': str(e) or e.__class__.__name__,
    }

    meta = getattr(e, 'meta', None)
    if meta:
        error['meta'] = dict(meta)

    error.setdefault('meta', {})['traceback'] = traceback.format_tb(sys.exc_info()[-1]),

    return Response(
        json.dumps({
            'error': error,
            'links': {'self': request.url},
        }), status, mimetype='application/json',
        headers=dict(getattr(e, 'headers', [])))


def unauthorized_error_handler(e: Exception) -> Response:
    """
    Error handling function for non-Afterglow HTTP 401 (UNAUTHORIZED) errors

    :param e: exception instance

    :return: JSON response object
    """
    return Response(
        json.dumps({
            'error': {
                'status': HTTP_STATUS_CODES[401],
                'id': e.__class__.__name__,
                'detail': str(e) or e.__class__.__name__,
            },
            'links': {'self': request.url},
        }), 401, mimetype='application/json')


def forbidden_error_handler(e: Exception) -> Response:
    """
    Error handling function for non-Afterglow HTTP 403 (FORBIDDEN) errors

    :param e: exception instance

    :return: JSON response object
    """
    return Response(
        json.dumps({
            'error': {
                'status': HTTP_STATUS_CODES[403],
                'id': e.__class__.__name__,
                'detail': str(e) or e.__class__.__name__,
            },
            'links': {'self': request.url},
        }), 403, mimetype='application/json')


def not_found_error_handler(e: Exception) -> Response:
    """
    Error handling function for non-Afterglow HTTP 404 (NOT FOUND) errors;
    raised when a nonexistent resource is requested

    :param e: exception instance

    :return: JSON response object
    """
    return Response(
        json.dumps({
            'error': {
                'status': HTTP_STATUS_CODES[404],
                'id': e.__class__.__name__,
                'detail': str(e) or e.__class__.__name__,
            },
            'links': {'self': request.url},
        }), 404, mimetype='application/json')


def internal_server_error_handler(e: Exception) -> Response:
    """
    Error handling function for non-Afterglow HTTP 500 (INTERNAL SERVER ERROR)
    errors

    :param e: exception instance

    :return: JSON response object
    """
    et, ev, etb = sys.exc_info()
    return Response(
        json.dumps({
            'error': {
                'status': HTTP_STATUS_CODES[500],
                'id': e.__class__.__name__,
                'detail': str(e) or e.__class__.__name__,
                'meta': {
                    'type': et.__name__,
                    'value': str(ev),
                    'traceback': traceback.format_tb(etb),
                },
            },
            'links': {'self': request.url},
        }), 500, mimetype='application/json')


class AfterglowErrorMeta(type):
    """
    Metaclass for class:`AfterglowError`; needed to automatically install error
    handler for each exception subclassing from `AfterglowError`, since Flask
    does not intercept subclassed exceptions in the base exception class
    handler
    """
    def __new__(mcs, *args, **kwargs):
        c = type.__new__(mcs, *args, **kwargs)
        exc_classes[c.__name__] = c
        return c


class AfterglowError(exceptions.HTTPException, metaclass=AfterglowErrorMeta):
    """
    Base class for all Afterglow Core exceptions

    :Attributes::
        code: HTTP status code for the exception, defaults to 400 (BAD REQUEST)
        id: unique string error code, e.g. exception class name
        meta: dictionary containing the optional exception attributes passed
            as keyword arguments when raising the exception and sent to the
            client in JSON
        headers: any additional HTTP headers to send
    """
    code = 400  # HTTP status code
    id: str = None  # Afterglow-specific error code
    meta: dict = None  # additional error data
    message: str = None  # error message

    def __init__(self, **kwargs):
        """
        Create an Afterglow exception instance

        :param kwargs: optional extra data sent to the client in the body of
            the error response; the special keyword "message" is always set to
            the error description text
        """
        super(AfterglowError, self).__init__()
        if self.id is None:
            self.id = self.__class__.__name__
        if not self.description and self.__doc__:
            self.description = self.__doc__
        self.meta = kwargs

    def __str__(self) -> str:
        """
        Return a string representation of an Afterglow error showing both error
        message and payload

        :return: stringified Afterglow error
        """
        msg = self.message
        if self.meta:
            msg += ' ({})'.format(
                ', '.join('{}={}'.format(name, val)
                          for name, val in self.meta.items()))
        return msg


class MethodNotImplementedError(AfterglowError):
    """
    Resource method is not implemented by the Afterglow Core. Mainly used
    by the data provider plugin system if the plugin class does not override
    the required abstract base DataProvider class method.

    Extra attributes::
        class_name: name of the class that must implement the method
        method_name: name of the method to implement
    """
    code = 501
    message = 'Method not implemented'


class ValidationError(AfterglowError):
    """
    Server-side validation fails for a certain field passed as a request
    parameter

    Extra attributes::
        field: name of the field
    """
    message = 'Validation failed'

    def __init__(self, field: str, message: Optional[str] = None,
                 code: Optional[int] = 400):
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
    message = 'Missing required data'


class NotAcceptedError(AfterglowError):
    """
    The client requested the MIME type that the server cannot return

    Extra attributes::
        accepted_mimetypes: Accept header value sent by the client
    """
    code = 406
    message = 'Sending data in the format requested by HTTP Accept header ' \
        'is not supported'
