from terrathings.connection import ConnectionPlugin, plugins
from terrathings.core.util import write_device_ip_to_cache, read_device_ip_from_cache


class PluginTemplate(ConnectionPlugin):
    required_properties = [
        {"name": "ip", "type": "string", "required": True},
    ]

    def get_deployment(self, device, properties):
        raise NotImplementedError()

    def initialize_device(self, runtime, device, properties):
        raise NotImplementedError()

    def update_full(self, runtime, device, properties):
        raise NotImplementedError()

    def update_partial(self, app, device, properties):
        raise NotImplementedError()


# plugins.register(PluginTemplate)
