"""
Afterglow Core: custom marshmallow schemas for API objects
"""

import datetime
from math import isinf, isnan
from typing import Union
from urllib.parse import quote

from flask import url_for
from marshmallow import Schema, fields, post_dump


__all__ = [
    'Boolean', 'DateTime', 'Date', 'Time', 'Float',
    'AfterglowSchema', 'Resource',
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
    def _serialize(self, value: Union[str, datetime.datetime, None], attr, obj,
                   **__):
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
            for name, val in self.dump(_obj).items():
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
                # noinspection PyTypeChecker
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
                        if hasattr(field, 'container') else field.inner.nested
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
        return self.dumps(self)


class Resource(AfterglowSchema):
    """
    Base class for Afterglow Core resources (data providers, data files, etc.)

    Provides JSON serialization of resource class fields based on marshmallow.
    Subclasses must define fields in the usual way:

    class MyResource(Resource):
        field1 = marshmallow.fields.Integer(...)

    Any other attributes and methods are allowed too. A special attribute
    __get_view__ defines the name of the view that is used to retrieve the
    resource by ID, e.g.

    from afterglow_core import Resource, url_prefix

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
