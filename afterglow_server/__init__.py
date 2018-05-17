"""
Afterglow Access Server: main app package
"""

from __future__ import absolute_import, division, print_function
import datetime
import json
from math import isinf, isnan
from marshmallow import Schema, fields
from werkzeug.datastructures import CombinedMultiDict, MultiDict
from flask import Flask, Response, request, url_for
from .__version__ import __version__, url_prefix


__all__ = [
    '__version__', 'url_prefix',
    'Float', 'AfterglowSchema', 'Resource',
    'app', 'json_response',
]


class Float(fields.Float):
    """
    Floating-point :class:`marshmallow.Schema` field that serializes NaNs and
    Infs to None
    """
    def _serialize(self, value, attr, obj):
        """
        Serializer for float fields

        :param value: value to serialize
        :param str attr: schema attribute name
        :param marshmallow.Schema obj: schema object

        :return: serialized value
        """
        try:
            if isinf(value) or isnan(value):
                return None
        except TypeError:
            pass

        return super(Float, self)._serialize(value, attr, obj)


class AfterglowSchema(Schema):
    """
    A :class:`marshmallow.Schema` subclass that allows initialization from an
    object or keyword arguments and explicitly assigns default values to all
    uninitialized fields. Serves as a self-contained schema that can both hold
    field values and dump itself to a dict or a JSON string.
    """
    def __init__(self, _obj=None, **kwargs):
        """
        Create a resource class instance

        resource = MyResource(field1=value1, ...)
            or
        resource = MyResource(sqla_object)

        :param _obj: initialize fields from the given object (usually an SQLA
            declarative instance)
        :param kwargs: keyword arguments are assigned to the corresponding
            instance attributes, including fields
        """
        super(AfterglowSchema, self).__init__()

        if _obj is not None:
            for name, val in self.dump(_obj).data.items():
                try:
                    if isinf(val) or isnan(val):
                        # Convert floating-point NaNs/Infs to string
                        val = str(val)
                except TypeError:
                    pass

                setattr(self, name, val)

        for name, val in kwargs.items():
            setattr(self, name, val)

        # Initialize the missing fields with their defaults or None
        for name, f in self.fields.items():
            if not hasattr(self, name):
                setattr(
                    self, name,
                    None if f.default == fields.missing_ else f.default)

    def __setattr__(self, name, value):
        """
        Deserialize fields on assignment

        :param str name: attribute name
        :param value: attribute value

        :return: None
        """
        if value is not None:
            try:
                field = self.fields[name]
            except (AttributeError, KeyError):
                pass
            else:
                if hasattr(field, 'nested') and \
                        issubclass(field.nested, AfterglowSchema):
                    value = field.nested(value)
                elif isinstance(field, fields.List) and \
                        hasattr(field.container, 'nested') and \
                        issubclass(field.container.nested, AfterglowSchema):
                    klass = field.container.nested
                    value = [klass(item) for item in value]
                elif value is not None:
                    # noinspection PyBroadException
                    try:
                        value = field.deserialize(value)
                    except Exception:
                        if isinstance(field, fields.DateTime) and \
                                isinstance(value, datetime.datetime) or \
                                isinstance(field, fields.Date) and \
                                isinstance(value, datetime.date) or \
                                isinstance(field, fields.Time) and \
                                isinstance(value, datetime.time):
                            pass
                        else:
                            raise
        super(AfterglowSchema, self).__setattr__(name, value)

    def json(self):
        """
        Serialize resource class instance to JSON

        :return: JSON string containing all resource fields plus its URI if
            the resource has ID
        :rtype: str
        """
        return self.dumps(self)[0]


class Resource(AfterglowSchema):
    """
    Base class for Afterglow Server resources (data providers, data files, etc.)

    Provides JSON serialization of resource class fields based on marshmallow.
    Subclasses must define fields in the usual way:

    class MyResource(Resource):
        field1 = marshmallow.fields.Integer(...)

    Any other attributes and methods are allowed too. A special attribute
    __get_view__ defines the name of the view that is used to retrieve the
    resource by ID, e.g.

    from afterglow_server import Resource, url_prefix

    class MyResource(Resource):
        __get_view__ = 'my_resource'
        id = Integer(default=None)
        ...

    @api.route(url_prefix + 'my_resource/[id]')
    def my_resource(id):
        ...
    """
    __get_view__ = None  # resource getter function name

    @property
    def _uri(self):
        if hasattr(self, 'id') and self.id is not None and \
                hasattr(self, '__get_view__') and self.__get_view__:
            return url_for(self.__get_view__, id=self.id, _external=True)
        raise AttributeError('_uri')

    uri = fields.String(attribute='_uri')


class ResourceEncoder(json.JSONEncoder):
    """
    JSON encoder that can serialize Resource class instances
    """
    def default(self, obj):
        if isinstance(obj, Resource):
            return obj.dump(obj)[0]
        if isinstance(obj, datetime.datetime):
            return obj.isoformat(' ')
        return super(ResourceEncoder, self).default(obj)


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
        json.dumps(obj, cls=ResourceEncoder), status_code,
        mimetype='application/json', headers=headers)


app = Flask(__name__)
app.config.from_object('afterglow_server.default_cfg')
app.config.from_envvar('AFTERGLOW_SERVER_CONFIG', silent=True)

if app.config.get('PROFILE'):
    # Enable profiling
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.config['DEBUG'] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[10])


def resolve_request_body():
    """
    Before every request, combine `request.form` and `request.get_json()` into
    `request.args`
    """
    ds = [request.args, request.form]

    body = request.get_json()
    if body:
        multi_dict_items = []
        for key, value in body.items():
            if isinstance(value, list):
                for item in value:
                    if not isinstance(item, list) and \
                            not isinstance(item, dict):
                        multi_dict_items.append((key, item))
            elif not isinstance(value, dict):
                multi_dict_items.append((key, value))

        ds.append(MultiDict(multi_dict_items))

    # Replace immutable Request.args with the combined args dict
    # noinspection PyPropertyAccess
    request.args = CombinedMultiDict(ds)


app.before_request(resolve_request_body)


# Initialize the user authentication engine
from . import auth
if app.config.get('USER_AUTH'):
    auth.init_auth()

# Initialize OAuth2 server if enabled
if app.config.get('OAUTH_CLIENTS'):
    from . import oauth2
    oauth2.init_oauth()

# Define API resources.
from .resources import *
