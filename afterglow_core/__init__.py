"""
Afterglow Core: main app package
"""

import datetime
import json
import os
import errno
from base64 import urlsafe_b64encode
from typing import Any, Dict as TDict, List as TList, Optional, Union

from flask_cors import CORS
from marshmallow import missing
from werkzeug.datastructures import CombinedMultiDict, MultiDict
from werkzeug.urls import url_encode
from flask import Flask, Response, request
from cryptography.fernet import Fernet
import astropy.io.fits as pyfits

from .schemas import AfterglowSchema


__all__ = ['app', 'cipher', 'json_response', 'PaginationInfo']


class AfterglowSchemaEncoder(json.JSONEncoder):
    """
    JSON encoder that can serialize AfterglowSchema class instances and
    datetime objects
    """

    def default(self, obj):
        if isinstance(obj, type(missing)) or isinstance(obj, pyfits.Undefined):
            return None
        if isinstance(obj, AfterglowSchema):
            return obj.dump(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat(' ')
        return super().default(obj)


class PaginationInfo(object):
    """
    Pagination info structure provided by resources that return multiple
    objects (e.g. data provider assets)

    Pagination info is returned in the JSON response envelope in the following
    way:
        {
            "data": [{object}, {object}, ...],
            "links": {
                "self": "resource URI",
                "pagination": {
                    "sort": "sorting mode (-mode = reverse)",
                    "first": "URL of first page (always present)",
                    "last": "URL of last page (always present)",
                    "prev": "URL of previous page (present unless first page)",
                    "next": "URL of next page (present unless last page)",
                    "page_size": # of items per page (always present),
                    "total_pages": optional total # of pages if known,
                    "current_page": optional 0-based current page index
                }
            }
        }

    Use :meth:`to_dict` to construct a JSON-serializable pagination structure.
    """
    sort: str = None  # sorting mode, optionally prefixed with + or -
    page_size: int = None  # page size
    total_pages: int = None  # total number of pages
    current_page: int = None  # 0-based current page index, page-based
    first_item: str = None  # key value of the first item on page, keyset-based
    last_item: str = None  # key value of the last item on page, keyset-based

    def __init__(self, sort: Optional[str] = None,
                 page_size: Optional[int] = None,
                 total_pages: Optional[int] = None,
                 current_page: Optional[int] = None,
                 first_item: Optional[Any] = None,
                 last_item: Optional[Any] = None):
        """

        :param sort: sorting mode, optionally prefixed with + or -
        :param page_size: page size
        :param total_pages: total number of pages
        :param current_page: 0-based current page index (page-based pagination)
        :param first_item: key value of the first item on page (keyset-based
            pagination)
        :param last_item: key value of the last item on page (keyset-based
            pagination)
        """
        if sort is not None:
            self.sort = str(sort)
        if page_size is not None:
            self.page_size = int(page_size)
        if total_pages is not None:
            self.total_pages = int(total_pages)
        if current_page is not None:
            self.current_page = int(current_page)
        if first_item is not None:
            self.first_item = str(first_item)
        if last_item is not None:
            self.last_item = str(last_item)

    def to_dict(self) -> dict:
        """
        Return a JSON-serializable dict constructed from the actual pagination
        info and request environment

        :return: pagination structure as dictionary
        """
        pagination = {}

        if self.current_page is None or self.current_page > 0:
            args = request.args.copy()
            try:
                del args['page[before]']
            except KeyError:
                pass
            try:
                del args['page[after]']
            except KeyError:
                pass
            args['page[number]'] = 'first'
            pagination['first'] = '{}?{}'.format(
                request.base_url, url_encode(args))

        if self.current_page is None or self.total_pages is None or \
                self.current_page < self.total_pages - 1:
            args = request.args.copy()
            try:
                del args['page[before]']
            except KeyError:
                pass
            try:
                del args['page[after]']
            except KeyError:
                pass
            args['page[number]'] = 'last'
            pagination['last'] = '{}?{}'.format(
                request.base_url, url_encode(args))

        for attr in ('sort', 'page_size', 'total_pages', 'current_page'):
            if getattr(self, attr, None) is not None:
                pagination[attr] = getattr(self, attr)

        if self.current_page is not None:
            # Page-based pagination
            if self.current_page > 0:
                args = request.args.copy()
                try:
                    del args['page[before]']
                except KeyError:
                    pass
                try:
                    del args['page[after]']
                except KeyError:
                    pass
                args['page[number]'] = str(self.current_page - 1)
                pagination['prev'] = '{}?{}'.format(
                    request.base_url, url_encode(args))
            if self.total_pages is None or \
                    self.current_page < self.total_pages - 1:
                args = request.args.copy()
                try:
                    del args['page[before]']
                except KeyError:
                    pass
                try:
                    del args['page[after]']
                except KeyError:
                    pass
                args['page[number]'] = str(self.current_page + 1)
                pagination['next'] = '{}?{}'.format(
                    request.base_url, url_encode(args))
        else:
            # Keyset-based pagination; first and last are keys for previous
            # and next pages
            if self.first_item is not None:
                args = request.args.copy()
                try:
                    del args['page[number]']
                except KeyError:
                    pass
                try:
                    del args['page[after]']
                except KeyError:
                    pass
                args['page[before]'] = str(self.first_item)
                pagination['prev'] = '{}?{}'.format(
                    request.base_url, url_encode(args))
            if self.last_item is not None:
                args = request.args.copy()
                try:
                    del args['page[number]']
                except KeyError:
                    pass
                try:
                    del args['page[before]']
                except KeyError:
                    pass
                args['page[after]'] = str(self.last_item)
                pagination['next'] = '{}?{}'.format(
                    request.base_url, url_encode(args))

        return pagination


def json_response(data: Optional[Union[dict, AfterglowSchema, TList[dict],
                                       TList[AfterglowSchema]]] = None,
                  status_code: Optional[int] = None,
                  headers: Optional[TDict[str, str]] = None,
                  pagination: Optional[PaginationInfo] = None,
                  force_pagination: bool = False) -> Response:
    """
    Serialize a Python object to a JSON-type flask.Response

    :param data: object(s) to serialize; can be a :class:`AfterglowSchema`
        instance or a dict, a list of those, or None
    :param int status_code: optional HTTP status code; defaults to 200 - OK
    :param dict headers: optional extra HTTP headers
    :param pagination: optional pagination info
    :param force_pagination: always include pagination links (first and last
        page) even if no total/previous/next page info is provided

    :return: Flask response object with mimetype set to application/json
    """
    links = {'self': request.url}
    if pagination is None and force_pagination:
        pagination = PaginationInfo()
    if pagination is not None:
        links['pagination'] = pagination.to_dict()
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

proxy_count = app.config.get('APP_PROXY')
if proxy_count:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=proxy_count, x_proto=proxy_count,
        x_host=proxy_count, x_port=proxy_count, x_prefix=proxy_count)

if app.config.get('APPLICATION_ROOT'):
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    app.wsgi_app = DispatcherMiddleware(
        app.wsgi_app, {app.config['APPLICATION_ROOT']: app.wsgi_app})

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


# Read/create secret key
keyfile = os.path.join(
    os.path.abspath(app.config['DATA_ROOT']), 'AFTERGLOW_CORE_KEY')
try:
    with open(keyfile, 'rb') as f:
        key = f.read()
except IOError:
    key = os.urandom(24)
    d = os.path.dirname(keyfile)
    if os.path.isfile(d):
        os.remove(d)
    try:
        os.makedirs(d)
    except OSError as _e:
        if _e.errno != errno.EEXIST:
            raise
    del d
    with open(keyfile, 'wb') as f:
        f.write(key)
app.config['SECRET_KEY'] = key
# Fernet requires 32-byte key, while Afterglow has been historically using
# 24-byte key
cipher = Fernet(urlsafe_b64encode(key + b'Afterglo'))
del f, key, keyfile


if app.config.get('AUTH_ENABLED'):
    # Initialize user authentication and enable non-versioned /users routes
    # and Afterglow OAuth2 server at /oauth2
    from . import auth


# Define API resources and endpoints
from . import resources, views
