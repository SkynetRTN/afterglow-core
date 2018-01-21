"""
Afterglow Access Server: plugin support
"""

from __future__ import absolute_import, division, print_function

import imp
import os
import zipfile
import zipimport

from . import app


__all__ = ['load_plugins']


def load_plugins(descr, package, plugin_class, specs):
    """
    Load and initialize plugins from the given directory

    :param str descr: plugin description
    :param str package: plugin package name relative to afterglow_server, e.g.
        "resources.data_provider_plugins"
    :param plugin_class: base plugin class
    :param list specs: list of plugin specifications: [{"name": "plugin_name",
        "param": value, ...}, ...]; parameters are used to construct the plugin
        class; this can be the value of the corresponding option in app config,
        e.g. DATA_PROVIDERS

    :return: dictionary containing plugin class instances indexed by their
        unique IDs (both as integers and strings)
    :rtype: dict
    """
    if not specs:
        # No plugins of this type are required
        return {}

    directory = os.path.normpath(os.path.join(
        os.path.dirname(__file__), package.replace('.', os.path.sep)))
    app.logger.debug('Looking for %s plugins in %s', descr, directory)

    # Obtain the list of valid Python module suffixes
    py_suffixes = [item[0] for item in imp.get_suffixes()]

    # Search for modules within the specified directory
    # noinspection PyBroadException
    try:
        # py2exe/freeze support
        if not isinstance(__loader__, zipimport.zipimporter):
            raise Exception()

        archive = zipfile.ZipFile(__loader__.archive)
        try:
            dirlist = [name for name in archive.namelist()
                       if name.startswith(directory.replace('\\', '/'))]
        finally:
            archive.close()
    except Exception:
        # Normal installation
        # noinspection PyBroadException
        try:
            dirlist = os.listdir(directory)
        except Exception:
            dirlist = []
    dirlist = [os.path.split(name)[1] for name in dirlist]

    plugin_classes = {}
    for name in {os.path.splitext(f)[0] for f in dirlist
                 if os.path.splitext(f)[1] in py_suffixes and
                 os.path.splitext(f)[0] != '__init__'}:
        # noinspection PyBroadException
        try:
            app.logger.debug('Checking module "%s"', name)
            # A potential plugin module is found; load it
            m = __import__(
                package + '.' + name, globals(), locals(), ['__dict__'])

            try:
                # Check only names listed in __all__
                items = (m.__dict__[_name] for _name in m.__dict__['__all__'])
            except KeyError:
                # If no __all__ is present in the module, check all globals
                items = m.__dict__.values()

            # Scan all items defined in the module, looking for classes
            # derived from "plugin_class"
            for item in items:
                try:
                    if issubclass(item, plugin_class) and \
                            item is not plugin_class and \
                            hasattr(item, 'name') and \
                            isinstance(item.name, str) and \
                            item.__module__ == m.__name__:
                        plugin_classes[item.name] = item
                        app.logger.debug(
                            'Found %s plugin "%s"', descr, item.name)
                except TypeError:
                    pass
        except Exception:
            # Ignore modules that could not be imported
            app.logger.debug(
                'Could not import module "%s"', name, exc_info=True)

    # Instantiate plugins using the specified display names and options
    plugins = {}
    for id, spec in enumerate(specs):
        try:
            name = spec.pop('name')
        except (TypeError, KeyError):
            raise RuntimeError(
                'Missing name in {} plugin spec ({})'.format(descr, spec))

        try:
            klass = plugin_classes[name]
        except KeyError:
            raise RuntimeError(
                'Unknown {} plugin "{}"'.format(descr, name))

        # Initialize plugin instance using the provided parameters
        try:
            instance = klass(**spec)
        except Exception:
            app.logger.exception(
                'Error loading %s plugin "%s" with options %s',
                descr, name, spec)
            raise

        if not hasattr(instance, 'display_name') or not instance.display_name:
            instance.display_name = instance.name

        if hasattr(instance, 'id') and instance.id is not None:
            # Plugin provides its own instance ID
            plugins[str(instance.id)] = instance
            try:
                instance.id = int(instance.id)
            except ValueError:
                pass
            else:
                plugins[instance.id] = instance
        else:
            # Use the automatically assigned integer instance ID
            instance.id = id
            plugins[id] = plugins[str(id)] = instance

        app.logger.info(
            'Loaded %s plugin "%s" (ID %s)',
            descr, instance.display_name, instance.id)

    return plugins
