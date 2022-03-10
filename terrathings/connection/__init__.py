import terrathings
from . import plugins
from .connection import ConnectionPlugin
from .deployment_status import (
    Runtime,
    Status,
    Deployment,
)
from terrathings.connection.plugins import registered_plugins
import inspect


def get_available_plugins():
    """
    Returns a list of all available plugins.
    """
    return [
        plugin
        for plugin in registered_plugins
        if (
            "get_deployment" in dir(plugin)
            and inspect.isfunction(plugin.get_deployment)
        )
        and (
            (
                "supportsInitialization" in dir(plugin)
                and not plugin.supportsInitialization
            )
            or (
                "initialize_device" in dir(plugin)
                and inspect.isfunction(plugin.initialize_device)
            )
        )
        and (
            ("supportsFullUpdate" in dir(plugin) and not plugin.supportsFullUpdate)
            or ("update_full" in dir(plugin) and inspect.isfunction(plugin.update_full))
        )
        and (
            (
                "supportsPartialUpdate" in dir(plugin)
                and not plugin.supportsPartialUpdate
            )
            or (
                "update_partial" in dir(plugin)
                and inspect.isfunction(plugin.update_partial)
            )
        )
    ]


def get_plugin_by_name(name) -> ConnectionPlugin | None:
    """
    Returns the plugin with the given name.

    :param str name: The name of the plugin.
    :return: The ConnectionPlugin with the given name.
    :rtype: ConnectionPlugin
    """
    for plugin in get_available_plugins():
        if plugin.__name__.lower() == name.lower():
            return plugin
    return None


def get_connection_plugin(connection_config) -> ConnectionPlugin:
    """
    Returns the connection plugin for the given connection config and validates the properties

    :param dict connection_config: The connection config
    :return: The connection plugin
    :rtype: ConnectionPlugin
    """
    plugin = get_plugin_by_name(connection_config["connection"])
    if plugin is None:
        raise ValueError(
            "Invalid connection plugin: {}".format(connection_config["connection"])
        )
    return plugin(
        properties=_get_properties_for_connection_plugin(plugin, connection_config),
    )


def _get_properties_for_connection_plugin(
    plugin: ConnectionPlugin, connection_config
) -> object:
    """
    Returns the properties for the given connection plugin and validates the properties

    :param ConnectionPlugin plugin: The connection plugin
    :param dict connection_config: The connection config

    :return: The properties for the connection plugin
    :rtype: object
    """

    # Fetches default properties
    connection_config_properties = (
        terrathings.connection.plugins.get_default_properties(plugin.__name__)
    )
    # Merges properties and overrides defaults on conflict
    if "properties" in connection_config:
        connection_config_properties.update(connection_config["properties"])

    properties = {}
    for attr in plugin.required_properties:
        if attr["name"] in connection_config_properties:
            properties[attr["name"]] = connection_config_properties[attr["name"]]
        elif attr["required"]:
            raise AttributeError("Missing required property: {}".format(attr["name"]))
    return properties
