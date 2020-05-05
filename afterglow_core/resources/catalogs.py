"""
Afterglow Core: catalog endpoint
"""

from __future__ import absolute_import, division, print_function

from .. import app, json_response, plugins, url_prefix
from ..auth import auth_required
from ..errors.catalog import UnknownCatalogError
from . import catalog_plugins


__all__ = ['catalogs']


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
        return json_response(catalogs)

    try:
        return json_response(catalogs[name])
    except KeyError:
        raise UnknownCatalogError(name=name)


# Load catalog plugins
catalogs = plugins.load_plugins(
    'catalog', 'resources.catalog_plugins', catalog_plugins.Catalog)
