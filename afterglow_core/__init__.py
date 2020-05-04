# TODO Improve organization of views, errors, db, and other files
# TODO Add database structure and management pages for API Token used in scripted access

"""
Afterglow Core: main app package
"""

from __future__ import absolute_import, division, print_function

import sys
import datetime
import json
import os

# noinspection PyProtectedMember
from marshmallow import (
    missing, __version_info__ as marshmallow_version)
from werkzeug.datastructures import CombinedMultiDict, MultiDict
from flask import Flask, Response

from .__version__ import __version__, url_prefix
from .models import AfterglowSchema

if sys.version_info.major < 3:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib import quote
else:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.parse import quote


__all__ = [
    '__version__', 'url_prefix',
    'app', 'json_response',
]


class AfterglowSchemaEncoder(json.JSONEncoder):
    """
    JSON encoder that can serialize AfterglowSchema class instances
    """
    def default(self, obj):
        if isinstance(obj, type(missing)):
            return None
        if isinstance(obj, AfterglowSchema):
            res = obj.dump(obj)
            if marshmallow_version < (3, 0):
                res = res[0]
            return res
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
app.config.from_object('afterglow_core.default_cfg')
app.config.from_envvar('AFTERGLOW_CORE_CONFIG', silent=True)

if app.config.get('PROFILE'):
    # Enable profiling
    from werkzeug.middleware.profiler import ProfilerMiddleware
    app.config['DEBUG'] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[10])

if app.config.get('OAUTH2_ALLOW_HTTP'):
    os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "1"


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


# Initialize the user authentication engine
from . import auth
# if app.config.get('USER_AUTH'):
#     auth.init_auth()
auth.init_auth()

# Initialize OAuth2 server if enabled
if app.config.get('OAUTH_CLIENTS'):
    from . import oauth2
    oauth2.init_oauth()

# Define API resources.
from .resources import *
from .views import *
