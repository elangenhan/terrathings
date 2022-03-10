from terrathings.connection import get_connection_plugin
from terrathings.connection.connection import ConnectionPlugin
import os


class Device:
    id: str
    runtime: str
    properties: dict
    init_connection: ConnectionPlugin
    update_connection: ConnectionPlugin

    def __init__(self, config: dict):
        self.id = config["id"]
        self.runtime = config["src"].split("/")[-1]
        self.src = config["src"]
        self.outfile = config["out_file"]
        self.properties = config.get("properties", [])
        self.init_connection = get_connection_plugin(config["init"])
        self.init_properties = config["init"].get("properties", {})
        self.init_cmd = config["init"].get("cmd", "")
        self.update_connection = get_connection_plugin(config["update"])
        self.update_properties = config["update"].get("properties", {})
        self.apps = config.get("applications", [])

    def init(self):
        """Initializes the device"""
        deployable_path = f"{os.getcwd()}/{self.src}build/{self.outfile}"
        self.init_connection.initialize_device(
            deployable_path, self, self.init_properties
        )

    def __repr__(self):
        return "<Device id={} type={} properties={}>".format(
            self.id, self.runtime, self.properties
        )

    def get_status(self):
        """Returns the status of the device"""
        status = self.update_connection.get_deployment(self, self.update_properties)
        if not status:
            status = self.init_connection.get_deployment(self, self.init_properties)

        return status

    def update_partial(self, deployment_id, config: dict):
        """Updates the device"""
        path_of_file = config["src"] + "build/app.wasm"

        return self.update_connection.update_partial(
            path_of_file, self, self.update_properties
        )

    def update_full(self, runtime_id, config: dict):
        path_of_file = f"{self.src}build/{self.outfile}"
        return self.update_connection.update_full(
            path_of_file, self, self.update_properties
        )

    def get_template_sha256(self):
        sha = os.popen(
            f"cd {os.getcwd()}/{self.src}"
            + ' && find . -type f -not -path "./.build.sha256" -not -path "./build/*" -not -path "./.pio/*" -print0 | sort -z | xargs -0 sha256sum | sha256sum'
        ).read()
        return sha.split(" ")[0]
