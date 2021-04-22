"""
Afterglow Core: main app package
"""

import datetime
import json
import os
from typing import Any, Dict as TDict, List as TList, Optional, Union

from flask_cors import CORS
from marshmallow import missing
from werkzeug.datastructures import CombinedMultiDict, MultiDict
from werkzeug.urls import url_encode
from flask import Flask, Response, request

from .schemas import AfterglowSchema


__all__ = ['app', 'json_response']


class PrefixMiddleware(object):
    def __init__(self, application, prefix=''):
        self.app = application
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response('404', [('Content-Type', 'text/plain')])
            return ["This url does not belong to the app.".encode()]


class AfterglowSchemaEncoder(json.JSONEncoder):
    """
    JSON encoder that can serialize AfterglowSchema class instances and datetime
    objects
    """
    def default(self, obj):
        if isinstance(obj, type(missing)):
            return None
        if isinstance(obj, AfterglowSchema):
            return obj.dump(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat(' ')
        return super().default(obj)


def json_response(data: Optional[Union[dict, AfterglowSchema, TList[dict],
                                       TList[AfterglowSchema]]] = None,
                  status_code: Optional[int] = None,
                  headers: Optional[TDict[str, str]] = None,
                  include_pagination: bool = False,
                  total_pages: Optional[int] = None,
                  first: Optional[Any] = None, last: Optional[Any] = None) \
        -> Response:
    """
    Serialize a Python object to a JSON-type flask.Response

    :param data: object(s) to serialize; can be a :class:`AfterglowSchema`
        instance or a dict, a list of those, or None
    :param int status_code: optional HTTP status code; defaults to 200 - OK
    :param dict headers: optional extra HTTP headers
    :param include_pagination: always include pagination links (first and last
        page) even if no total/previous/next page info is provided
    :param total_pages: optional extra pagination info: total number of pages
    :param first: optional extra pagination info: for keyset-nased pagination,
        this is the key value for the first item on the current page; for
        page-based pagination, this is the current page number; used
        to construct the link to the previous page
    :param last: optional extra pagination info: for keyset-based pagination,
        this is the key value for the last item on the current page or None
        otherwise; used to construct the link to the next page

    :return: Flask response object with mimetype set to application/json
    """
    links = {'self': request.url}
    if include_pagination or (total_pages, first, last) != (None,)*3:
        # Add pagination info
        args_first = request.args.copy()
        args_first['page[number]'] = 'first'
        args_last = request.args.copy()
        args_last['page[number]'] = 'last'
        pagination = {
            # Always have links to first and last pages
            'first': '{}?{}'.format(request.base_url, url_encode(args_first)),
            'last': '{}?{}'.format(request.base_url, url_encode(args_last)),
        }
        if total_pages is not None:
            pagination['total_pages'] = total_pages
        if first is not None:
            if last is None:
                # Page-based pagination; first is page number
                if first > 0:
                    args = request.args.copy()
                    args['page[number]'] = str(first - 1)
                    pagination['prev'] = '{}?{}'.format(
                        request.base_url, url_encode(args))
                if total_pages is None or first < total_pages - 1:
                    args = request.args.copy()
                    args['page[number]'] = str(first + 1)
                    pagination['next'] = '{}?{}'.format(
                        request.base_url, url_encode(args))
            else:
                # Keyset-based pagination; first and last are keys for previous
                # and next pages
                args = request.args.copy()
                args['page[before]'] = str(first)
                pagination['prev'] = '{}?{}'.format(
                    request.base_url, url_encode(args))
                args = request.args.copy()
                args['page[after]'] = str(last)
                pagination['next'] = '{}?{}'.format(
                    request.base_url, url_encode(args))
        links['pagination'] = pagination
    envelope = {
        'data': data,
        'links': links,
    }
    return Response(
        json.dumps(envelope, cls=AfterglowSchemaEncoder),
        status_code or 200, mimetype='application/json', headers=headers)


app = Flask(__name__)
cors = CORS(app, resources={'/api/*': {'origins': '*'}})
app.config.from_object('afterglow_core.default_cfg')
app.config.from_envvar('AFTERGLOW_CORE_CONFIG', silent=True)

if app.config.get('APP_PREFIX'):
    app.wsgi_app = PrefixMiddleware(
        app.wsgi_app, prefix=app.config.get('APP_PREFIX'))

if app.config.get('PROFILE'):
    # Enable profiling
    from werkzeug.middleware.profiler import ProfilerMiddleware
    app.config['DEBUG'] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[10])

if app.config.get('OAUTH2_ALLOW_HTTP') or app.config.get('DEBUG'):
    os.environ['AUTHLIB_INSECURE_TRANSPORT'] = '1'


@app.before_request
def resolve_request_body() -> None:
    """
    Before every request, combine `request.form` and `request.get_json()` into
    `request.args`
    """
    ds = [request.args, request.form]

    body = request.get_json()
    if body:
        ds.append(MultiDict(body.items()))

    # Replace immutable Request.args with the combined args dict
    # noinspection PyPropertyAccess
    request.args = CombinedMultiDict(ds)


if app.config.get('AUTH_ENABLED'):
    # Initialize user authentication and enable non-versioned /users routes
    # and Afterglow OAuth2 server at /oauth2
    from . import auth


# Define API resources and endpoints
from . import resources, views
