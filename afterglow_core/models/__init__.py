"""
Afterglow Core: object data models

Afterglow Core object data model is essentially a customized marshmallow
self-serializable schema subclassing from
:class:`afterglow_core.schemas.AfterglowSchema`. Such models have a predefined
set of typed fields and can be deserialized (loaded) from another object or
a dictionary of field-value pairs and serialized to a dictionary.

Some of these models, like users, data files, field cals, and jobs, correspond
to an underlying database object. Such objects are defined in the corresponding
:mod:`afterglow_core.resources` modules and still have serializable wrappers
in :mod:`afterglow_core.models`, which serve as an extra isolation layer
to facilitate an easier interaction with API schemas and to exchange data
between the job server and the job worker processes. Other data models, like
catalogs, data providers, and photometry data structures, do not have a database
counterpart. For them, a data model instance defined here serves as the only
representation of the data; it stores the object on the duration of the API
request and is directly serialized to an API schema. This can be schematically
illustrated by the following diagram:

     Database        |    Data Model                API
(:mod:`resources`)   | (:mod:`models`)     (:mod:`schemas.api.v*`)
                     |
     DbObject       <->     Object    <->       ObjectSchema
     (db_obj)                (obj)                (schema)

           |                |  |                   |
            :mod:`resources`    :mod:`views.api.v*`

where the leftmost part is optional.

The conversion between these layers is done as follows:

      Conversion                       Code                          Module
Database -> Data Model     obj = Object(db_obj)                   resources
Data Model -> API          schema = ObjectSchema(obj)             views.api.v*
API -> Data Model          obj = Object(schema)                   views.api.v*
Data Model -> Database     db_obj = DbObject(**obj.to_dict())     resources
"""

from .catalogs import *
from .data_files import *
from .data_providers import *
from .field_cals import *
from .jobs import *
from .photometry import *
from .source_extraction import *
from .users import *
