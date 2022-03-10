from . import connection
from .core import cli, device_manager


def main():
    action, devices, config, deployment = cli.init()

    connection.plugins.load()

    if action == "build":
        device_manager.build(config, devices, deployment)
    elif action == "init":
        device_manager.init(config, devices, True)
    elif action == "update":
        device_manager.update(config, devices, deployment)
    elif action == "apply":
        device_manager.apply(config, devices)
