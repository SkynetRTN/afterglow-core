"""
Afterglow Access Server: main app package
"""

from __future__ import absolute_import, division, print_function

import sys
import datetime
import json
from math import isinf, isnan

from marshmallow import (
    Schema, fields, missing, post_dump, __version_info__ as marshmallow_version)
from werkzeug.datastructures import CombinedMultiDict, MultiDict
from flask import Flask, Response, request, url_for

from .__version__ import __version__, url_prefix

if sys.version_info.major < 3:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib import quote
else:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.parse import quote


__all__ = [
    '__version__', 'url_prefix',
    'Boolean', 'DateTime', 'Date', 'Time', 'Float',
    'AfterglowSchema', 'Resource',
    'app', 'json_response',
]


class Boolean(fields.Boolean):
    """
    Use this instead of :class:`marshmallow.fields.Boolean` to allow assigning
    values such as "yes" and "no"
    """
    truthy = {
        True, 't', 'T', 'true', 'True', 'TRUE', 'yes', 'Yes', 'YES', 'on', 'On',
        'ON', '1', 1, 1.0}
    falsy = {
        False, 'f', 'F', 'false', 'False', 'FALSE', 'no', 'No', 'NO', 'off',
        'Off', 'OFF', '0', 0, 0.0}


class DateTime(fields.DateTime):
    """
    Use this instead of :class:`marshmallow.fields.DateTime` to make sure that
    the data stored in JSONType database columns is deserialized properly
    """
    def _serialize(self, value, attr, obj, **__):
        if value is None or isinstance(value, str) or \
                isinstance(value, type(u'')):
            return value
        return value.strftime('%Y-%m-%d %H:%M:%S.%f')


class Date(fields.Date):
    """
    Use this instead of :class:`marshmallow.fields.Date` to make sure that
    the data stored in JSONType database columns is deserialized properly
    """
    def _serialize(self, value, attr, obj, **__):
        if isinstance(value, str) or isinstance(value, type(u'')):
            return value
        return super(Date, self)._serialize(value, attr, obj)


class Time(fields.Time):
    """
    Use this instead of :class:`marshmallow.fields.Time` to make sure that
    the data stored in JSONType database columns is deserialized properly
    """
    def _serialize(self, value, attr, obj, **__):
        if isinstance(value, str) or isinstance(value, type(u'')):
            return value
        return super(Time, self)._serialize(value, attr, obj)


class Float(fields.Float):
    """
    Floating-point :class:`marshmallow.Schema` field that serializes NaNs and
    Infs to None
    """
    def _serialize(self, value, attr, obj, **__):
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
            data = self.dump(_obj)
            if marshmallow_version < (3, 0):
                data = data[0]
            for name, val in data.items():
                try:
                    if isinf(val) or isnan(val):
                        # Convert floating-point NaNs/Infs to string
                        val = str(val)
                except TypeError:
                    pass

                if val is not None:
                    setattr(self, name, val)

        for name, val in kwargs.items():
            if name in self._declared_fields and val is not None:
                setattr(self, name, val)

        # Initialize the missing fields with their defaults
        for name, f in self.fields.items():
            if not hasattr(self, name) and f.default != fields.missing_:
                try:
                    setattr(self, name, f.default)
                except AttributeError:
                    # Possibly missing attribute with a default in the base
                    # class was turned into a read-only property in a subclass
                    pass

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
                elif isinstance(field, fields.List) and (
                        (hasattr(field.container, 'nested') and
                         issubclass(field.container.nested, AfterglowSchema))
                        if hasattr(field, 'container')
                        else hasattr(field.inner, 'nested') and
                        issubclass(field.inner.nested, AfterglowSchema)):
                    klass = field.container.nested \
                        if hasattr(field, 'container') else field.inner
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
                        elif isinstance(field, fields.String):
                            value = field.deserialize(str(value))
                        else:
                            raise
        super(AfterglowSchema, self).__setattr__(name, value)

    @post_dump
    def remove_nones(self, data, **__):
        """
        Don't dump fields containing None

        :param data: serialized schema

        :return: input data with Non-valued fields stripped
        :rtype: dict
        """
        return {key: value for key, value in data.items() if value is not None}

    def json(self):
        """
        Serialize resource class instance to JSON

        :return: JSON string containing all resource fields plus its URI if
            the resource has ID
        :rtype: str
        """
        res = self.dumps(self)
        if marshmallow_version < (3, 0):
            res = res[0]
        return res


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
        if hasattr(self, '__get_view__') and self.__get_view__:
            for attr in ('id', 'name'):
                if getattr(self, attr, None) is not None:
                    return url_for(self.__get_view__, _external=True) + '/' + \
                        quote(str(getattr(self, attr)))
        raise AttributeError('_uri')

    uri = fields.String(attribute='_uri')


class AfterglowSchemaEncoder(json.JSONEncoder):
    """
    JSON encoder that can serialize AfterglowSchema class instances
    """
    def default(self, obj):
        if isinstance(obj, type(missing)):
            return None
        if isinstance(obj, AfterglowSchema):
            res = obj.dump()
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
app.config.from_object('afterglow_server.default_cfg')
app.config.from_envvar('AFTERGLOW_SERVER_CONFIG', silent=True)

if app.config.get('PROFILE'):
    # Enable profiling
    from werkzeug.middleware.profiler import ProfilerMiddleware
    app.config['DEBUG'] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[10])


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
if app.config.get('USER_AUTH'):
    auth.init_auth()

# Initialize OAuth2 server if enabled
if app.config.get('OAUTH_CLIENTS'):
    from . import oauth2
    oauth2.init_oauth()

# Define API resources.
from .resources import *
