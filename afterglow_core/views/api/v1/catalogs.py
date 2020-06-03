"""
Afterglow Core: API v1 catalog views
"""

from .... import app, json_response
from ....auth import auth_required
from ....resources.catalogs import catalogs
from ....errors.catalog import UnknownCatalogError
from . import url_prefix


resource_prefix = url_prefix + 'catalogs/'


@app.route(resource_prefix[:-1])
@app.route(resource_prefix + '<name>')
@auth_required('user')
def get_catalogs(name=None):
    """
    Return available catalog description(s)

    GET /catalogs
        - return a list of all available catalogs

    GET /catalogs/[name]
        - return a single catalog with the given name

    :param str name: catalog name

    :return: JSON response containing the list of serialized catalog objects
        when no name supplied or a single catalog otherwise
    :rtype: flask.Response
    """
    if name is None:
        # List all catalogs
        return json_response(list(catalogs.values()))

    try:
        return json_response(catalogs[name])
    except KeyError:
        raise UnknownCatalogError(name=name)
