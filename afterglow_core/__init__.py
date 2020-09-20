"""
Afterglow Core: main app package
"""

import sys
import datetime
import json
import os

from flask_cors import CORS
from marshmallow import missing
from werkzeug.datastructures import CombinedMultiDict, MultiDict
from flask import Flask, Response

from .schemas import AfterglowSchema

if sys.version_info.major < 3:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib import quote
else:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.parse import quote


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
    JSON encoder that can serialize AfterglowSchema class instances
    """
    def default(self, obj):
        if isinstance(obj, type(missing)):
            return None
        if isinstance(obj, AfterglowSchema):
            return obj.dump(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat(' ')
        return super(AfterglowSchemaEncoder, self).default(obj)


def json_response(obj='', status_code=None, headers=None):
    """
    Serialize a Python object to a JSON-type flask.Response

    :param obj: object to serialize; can be a Resource instance or a compound
        object (list, dict, ...) possibly including Resource instances
    :param int status_code: optional HTTP status code; defaults to 200 - OK
    :param dict headers: optional extra HTTP headers

    :return: Flask response object with mimetype set to application/json
    :rtype: `flask.Response`
    """
    if obj == '' or status_code == 204:
        resp = Response('', 204, headers=headers)
        del resp.headers['Content-Type']
        return resp

    if status_code is None:
        status_code = 200
    return Response(
        json.dumps(obj, cls=AfterglowSchemaEncoder), status_code,
        mimetype='application/json', headers=headers)


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
def resolve_request_body():
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
from .resources import *
from .views import *
