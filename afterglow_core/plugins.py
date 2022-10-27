"""
Afterglow Core: plugin support
"""

from __future__ import absolute_import, division, print_function

import os
import zipfile
import zipimport
from typing import Any, Dict as TDict, List as TList, Union

from flask import current_app as app

# List of valid Python module suffixes
try:
    # noinspection PyCompatibility
    from importlib.machinery import all_suffixes
    PY_SUFFIXES = all_suffixes()
except ImportError:
    # noinspection PyDeprecation
    from imp import get_suffixes
    PY_SUFFIXES = [item[0] for item in get_suffixes()]
    all_suffixes = None


__all__ = ['load_plugins']


def add_plugin(plugins: TDict[Union[str, int], Any], descr: str, instance: Any,
               default_id: int = None) -> None:
    """
    Add a plugin instance to the plugin dictionary, with the possible alias for
    integer plugin IDs; adjust plugin ID and display name; check that there are
    no more plugins with the same name if allow_multiple_instances is False

    :param plugins: dictionary {str(id): instance, int(id): instance}
    :param descr: plugin description
    :param instance: plugin class instance
    :param default_id: numeric ID assigned to plugin by default

    :return: None
    """
    if getattr(instance, 'name', None) and \
            not getattr(instance, 'allow_multiple_instances', True) and \
            any(getattr(other_instance, 'name', None) == instance.name and
                other_instance is not instance
                for other_instance in plugins.values()):
        raise RuntimeError('Multiple instances of plugin "{}" are not allowed'
                           .format(instance.name))

    if not hasattr(instance, 'display_name') or \
            not instance.display_name:
        instance.display_name = getattr(instance, instance.__polymorphic_on__)

    if hasattr(instance, 'id') and instance.id is not None:
        id = instance.id
    else:
        id = getattr(instance, instance.__polymorphic_on__)
        # noinspection PyBroadException
        try:
            instance.id = id
        except Exception:
            if default_id is not None:
                instance.id = default_id
                plugins[default_id] = plugins[str(default_id)] = instance
    plugins[str(id)] = instance
    try:
        instance.id = int(id)
    except ValueError:
        pass
    else:
        plugins[instance.id] = instance

    app.logger.info(
        'Loaded %s plugin "%s"%s', descr, instance.display_name,
        ' (ID {})'.format(instance.id) if instance.id is not None else '')


def load_plugins(descr: str, package: str, plugin_class: Any,
                 specs: TList[TDict[str, Any]] = None) -> \
        TDict[Union[str, int], Any]:
    """
    Load and initialize plugins from the given directory

    :param descr: plugin description
    :param package: plugin package name relative to afterglow_core, e.g.
        "resources.data_provider_plugins"
    :param plugin_class: base plugin class
    :param specs: list of plugin specifications: [{"name": "plugin_name",
        "param": value, ...}, ...]; parameters are used to construct the plugin
        class; this can be the value of the corresponding option in app config,
        e.g. DATA_PROVIDERS; if omitted or None, load all available plugins
        without passing any parameters on initialization (suitable e.g. for the
        jobs)

    :return: dictionary containing plugin class instances indexed by their
        unique IDs (both as integers and strings)
    """
    if not specs and specs is not None:
        # No plugins of this type are required
        return {}

    directory = os.path.normpath(os.path.join(
        os.path.dirname(__file__), package.replace('.', os.path.sep)))
    app.logger.debug('Looking for %s plugins in %s', descr, directory)

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
                 if os.path.splitext(f)[1] in PY_SUFFIXES and
                 os.path.splitext(f)[0] != '__init__'}:
        # noinspection PyBroadException
        try:
            app.logger.debug('Checking module "%s"', name)
            # A potential plugin module is found; load it
            m = __import__(
                'afterglow_core.' + package + '.' + name, globals(), locals(),
                ['__dict__'])

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
                            getattr(item, '__polymorphic_on__', None) and \
                            hasattr(item, item.__polymorphic_on__) and \
                            isinstance(getattr(item, item.__polymorphic_on__),
                                       str) and \
                            item.__module__ == m.__name__:
                        plugin_classes[getattr(item,
                                               item.__polymorphic_on__)] = item
                        app.logger.debug(
                            'Found %s plugin "%s"', descr,
                            getattr(item, item.__polymorphic_on__))
                except TypeError:
                    pass
        except Exception:
            # Ignore modules that could not be imported
            app.logger.debug(
                'Could not import module "%s"', name, exc_info=True)

    plugins = {}
    if specs is None:
        # Initialize all available plugins without any options
        for name, klass in plugin_classes.items():
            # Initialize plugin instance; provide the polymorphic field equal
            # to plugin name to instantiate the appropriate subclass instead
            # of the base plugin class
            try:
                instance = klass(
                    **{klass.__polymorphic_on__:
                       getattr(klass, klass.__polymorphic_on__)})
            except Exception:
                app.logger.exception(
                    'Error loading %s plugin "%s"', descr, name)
                raise

            add_plugin(plugins, descr, instance)
    else:
        # Instantiate only the given plugins using the specified display names
        # and options
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

            add_plugin(plugins, descr, instance, id)

    return plugins
