"""
Afterglow Core: API v1 catalog views
"""

from typing import Optional

from flask import Response

from .... import app, json_response
from ....auth import auth_required
from ....resources.catalogs import catalogs
from ....schemas.api.v1 import CatalogSchema
from ....errors.catalog import UnknownCatalogError
from . import url_prefix


resource_prefix = url_prefix + 'catalogs/'


@app.route(resource_prefix[:-1])
@app.route(resource_prefix + '<name>')
@auth_required('user')
def get_catalogs(name: Optional[str] = None) -> Response:
    """
    Return available catalog description(s)

    GET /catalogs
        - return a list of all available catalogs

    GET /catalogs/[name]
        - return a single catalog with the given name

    :param str name: catalog name

    :return: JSON response containing the list of serialized catalog objects
        when no name supplied or a single catalog otherwise
    """
    if name is None:
        # List all catalogs
        return json_response([CatalogSchema(cat) for cat in catalogs.values()])

    try:
        return json_response(CatalogSchema(catalogs[name]))
    except KeyError:
        raise UnknownCatalogError(name=name)
