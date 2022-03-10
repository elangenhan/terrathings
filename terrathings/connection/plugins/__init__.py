import pkgutil
from terrathings.connection.connection import ConnectionPlugin
import terrathings.connection.plugins
import importlib.util
from terrathings.core.logging import logging as log

default_properties: dict = {}
registered_plugins = []


def register(plugin: ConnectionPlugin):
    registered_plugins.append(plugin)


def get_default_properties(identifier) -> dict:
    if identifier.lower() in default_properties:
        return default_properties[identifier.lower()]
    else:
        return {}


def load():
    """read available files in this directory"""
    for item in pkgutil.iter_modules(terrathings.connection.plugins.__path__):
        try:
            spec = importlib.util.spec_from_file_location(
                item.name, f"{item[0].path}/{item.name}.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except ImportError as e:
            log.warning(e)
