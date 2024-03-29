"""
Afterglow Core: custom marshmallow schemas for API objects
"""

import datetime
from math import isinf, isnan
from typing import Any, Dict as TDict, Optional, Set, Sequence, Type, Union
from urllib.parse import quote

from flask import url_for
from marshmallow import Schema, fields, post_dump


__all__ = [
    'Boolean', 'DateTime', 'Date', 'Time', 'Float', 'NestedPoly',
    'AfterglowSchema', 'Resource',
]


class Boolean(fields.Boolean):
    """
    Use this instead of :class:`marshmallow.fields.Boolean` to allow assigning
    values such as "yes" and "no"
    """
    truthy = {
        True, 't', 'T', 'true', 'True', 'TRUE', 'yes', 'Yes', 'YES', 'on',
        'On', 'ON', '1', 1, 1.0}
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
        return super()._serialize(value, attr, obj)


class Time(fields.Time):
    """
    Use this instead of :class:`marshmallow.fields.Time` to make sure that
    the data stored in JSONType database columns is deserialized properly
    """
    def _serialize(self, value, attr, obj, **__):
        if isinstance(value, str) or isinstance(value, type(u'')):
            return value
        return super()._serialize(value, attr, obj)


class Float(fields.Float):
    """
    Floating-point :class:`marshmallow.Schema` field that serializes NaNs and
    Infs to None
    """
    def __init__(self, *, allow_nan: bool = True, **kwargs):
        super().__init__(allow_nan=allow_nan, **kwargs)

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

        return super()._serialize(value, attr, obj)


class NestedPoly(fields.Nested):
    """
    Nested field containing a polymorphic schema
    """
    def _serialize(self, value, attr, obj, **__):
        if isinstance(value, Schema):
            return value.dump(value, many=value.many or self.many)
        if isinstance(value, dict):
            # noinspection PyCallingNonCallable
            return self.nested(value).dump(value, many=self.many)
        return super()._serialize(value, attr, obj)


class AfterglowSchema(Schema):
    """
    A :class:`marshmallow.Schema` subclass that allows initialization from an
    object or keyword arguments and explicitly assigns default values to all
    uninitialized fields. Serves as a self-contained schema that can both hold
    field values and dump itself to a dict or a JSON string.

    :class:`AfterglowSchema` supports polymorphic schemas. If the special
    attribute `__polymorphic_on__` is set to the name of one of the attributes,
    AfterglowSchema(...) , instead of returning the base class instance, will
    return an instance of one of its immediate subclasses that has the value
    of the corresponding attribute equal to the value provided on creation,
    either in the initializer object or in the keyword arguments (see
    :meth:`__init__`).
    """
    __polymorphic_on__ = None

    _remove_nulls = False  # remove null-valued fields on dump

    def __new__(cls, _obj: Any = None, **kwargs):
        # Handle polymorphism
        poly_attr = cls.__polymorphic_on__
        if poly_attr is not None:
            # Find the appropriate subclass to instantiate based
            # on the polymorphic identity provided in _obj or kwargs
            try:
                poly_identity = getattr(_obj, poly_attr)
            except AttributeError:
                try:
                    poly_identity = _obj[poly_attr]
                except (KeyError, TypeError):
                    try:
                        poly_identity = kwargs[poly_attr]
                    except KeyError:
                        poly_identity = None
            if poly_identity is not None:
                subclass = find_polymorphic_class(
                    cls, poly_attr, poly_identity)
                if subclass is not None:
                    cls = subclass
                    if cls.__polymorphic_on__ != poly_attr:
                        # Handle multi-level polymorphism
                        return AfterglowSchema.__new__(cls, _obj, **kwargs)

        # Instantiate the class
        return super().__new__(cls)

    def __init__(self, _obj: Any = None,
                 only: Optional[Union[Sequence[str], Set[str]]] = None,
                 exclude: Union[Sequence[str], Set[str]] = (),
                 _remove_nulls: bool = False, **kwargs):
        """
        Create an Afterglow schema class instance

        schema = MySchema(field1=value1, ...)
            or
        schema = MySchema(object)

        :param _obj: initialize fields from the given object (usually a data
            model object defined in :mod:`afterglow_core.models`, an SQLA
            database object defined in :mod:`afterglow_core.resources`),
            or a public API schema defined in :mod:`afterglow_core.schemas.api`
        :param only: whitelist of the fields to include in the instantiated
            schema
        :param exclude: blacklist of the fields to exclude
            from the instantiated schema
        :param _remove_nulls: if set, don't dump fields with null values
        :param kwargs: keyword arguments are assigned to the corresponding
            instance attributes, including fields
        """
        self._remove_nulls = _remove_nulls
        super().__init__(partial=True, only=only, exclude=exclude)

        if _obj is None:
            kw = kwargs
        else:
            kw = dict(self.dump(_obj))
            kw.update(kwargs)

        # Initialize fields passed via keywords or object instance
        for name, val in kw.items():
            try:
                if isinf(val) or isnan(val):
                    # Convert floating-point NaNs/Infs to string
                    val = str(val)
            except TypeError:
                pass

            setattr(self, name, val)

        # Initialize missing fields with their defaults
        for name, f in self.dump_fields.items():
            if not hasattr(self, name) and f.dump_default != fields.missing_:
                try:
                    setattr(self, name, f.dump_default)
                except AttributeError:
                    # Possibly missing attribute with a default in the base
                    # class was turned into a read-only property
                    # in a subclass
                    pass

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Deserialize fields on assignment

        :param name: attribute name
        :param value: attribute value
        """
        if value is not None:
            try:
                field = self.fields[name]
            except (AttributeError, KeyError):
                pass
            else:
                if not field.load_only:
                    # Include field in serialization
                    self.dump_fields[name] = field
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
        super().__setattr__(name, value)

    @post_dump
    def remove_nones(self, data: TDict[str, Any], **__) -> TDict[str, Any]:
        """
        Don't dump None-valued fields

        :param data: serialized schema

        :return: input data with Non-valued fields stripped
        """
        if self._remove_nulls:
            return {key: value for key, value in data.items()
                    if value is not None}
        return data

    def to_dict(self) -> TDict[str, Any]:
        """
        Serialize resource class instance to dictionary

        :return: dictionary containing all resource fields
        """
        return self.dump(self)

    def json(self) -> str:
        """
        Serialize resource class instance to JSON

        :return: JSON string containing all resource fields
        """
        return self.dumps(self)


def find_polymorphic_class(
        cls: Type[AfterglowSchema], poly_attr: str, poly_identity: str) \
        -> Optional[Type[AfterglowSchema]]:
    for subclass in cls.__subclasses__():
        if getattr(subclass, poly_attr, None) == poly_identity:
            return subclass

        if subclass.__subclasses__():
            poly_class = find_polymorphic_class(
                subclass, poly_attr, poly_identity)
            if poly_class is not None:
                return poly_class


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
        __get_view__ = 'my_resources.my_resource'
        id = Integer(dump_default=None)
        ...

    blp = Blueprint('my_resources', __name__, url_prefix='/my_resources')
    @blp.route('/[id]')
    def my_resource(id):
        ...
    """
    __get_view__ = None  # resource getter function name

    @property
    def _uri(self):
        if hasattr(self, '__get_view__') and self.__get_view__:
            for attr in ('id', 'name'):
                if getattr(self, attr, None) is not None:
                    return url_for(self.__get_view__, _external=True) + '/' + quote(str(getattr(self, attr)))
        raise AttributeError('_uri')

    uri = fields.String(attribute='_uri')
