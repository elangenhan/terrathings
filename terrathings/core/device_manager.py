import base64
import os

from terrathings.connection import deployment_status
from terrathings.core.device import Device
from terrathings.core.shell import exec
from terrathings.core.util import (
    get_sha256_hash,
    sign_file,
)
from terrathings.core.logging import logging as log


def build(config, devices, app_id):
    """
    Builds the runtimes for given devices and given applications without applying them to devices.

    :param dict config: the extracted configuration from the provided config file
    :param list[dict] devices: list of devices to apply the applications to, if None config will be applied to all devices
    :param str app_ids: the id of an apps to build
    """

    if app_id:
        compile_apps([x for x in config["applications"] if x["id"] == app_id])
        return

    if devices:
        filtered_devices = list(filter(lambda d: d["id"] in devices, config["devices"]))
        compile_apps(config["applications"])
        compile_runtimes(filtered_devices)
    else:
        compile_apps(config["applications"])
        compile_runtimes(config["devices"])


def init(config, filter_by_device_ids, manual=False):
    """If a list of devices is provided, only initialize those devices."""

    if filter_by_device_ids:
        devices = [x for x in config["devices"] if x["id"] in filter_by_device_ids]
    else:
        devices = config["devices"]

    if not manual:
        devices = list(
            filter(
                lambda d: d["init"].get("manual", False) == False,
                devices,
            )
        )

    compile_runtimes(devices)
    init_devices(devices)


def update(config, filter_devices, filter_apps_by_ids):
    """
    Updates the runtime on given devices

    :param dict config: the extracted configuration from the provided config file
    :param list filter_devices: list of devices to update, if None all devices will be updated
    :param list filter_deployment: list of applications to update, if None all applications will be updated
    """

    devices = config["devices"]
    if filter_devices:
        devices = list(filter(lambda d: d["id"] in filter_devices, config["devices"]))

    apps = config["applications"]
    if filter_apps_by_ids:
        apps = [x for x in apps if x["id"] == filter_apps_by_ids]
        compile_apps(apps)
        update_partial(devices, apps)

    if not filter_apps_by_ids:
        compile_apps(apps)
        compile_runtimes(devices)
        update_devices(devices, apps)


def apply(config, devices):
    """
    Initializes and updates the given devices, if required

    :param dict config: the extracted configuration from the provided config file
    :param list devices: list of devices to apply the applications to, if None config will be applied to all devices
    """
    init(config, devices)
    update(config, devices, None)


def compile_runtimes(devices):
    """
    Compile the runtime for given devices

    :param list devices: list of devices to compile the runtime for
    """

    log.debug(
        f"Compiling runtimes for {len(devices)} devices: {[x['id'] for x in devices]}"
    )

    for device_config in devices:
        device = Device(device_config)

        previous_build_sha256 = None
        build_sha256_file = f"{os.getcwd()}/{device_config['src']}.build.sha256"
        try:
            with open(build_sha256_file, "r") as f:
                previous_build_sha256 = f.read()
        except Exception:
            log.info(f"No previous build found for runtime: {device.id}")

        with open(f"{build_sha256_file}.properties", "w") as f:
            f.write(str(device.properties))

        current_build_sha256 = device.get_template_sha256()
        if current_build_sha256 != previous_build_sha256:
            log.info(f"Compiling runtime: {device.id}")

            exec(
                device_config["build_cmd"],
                f"{os.getcwd()}/{device_config['src']}",
                {**device_config["properties"]},
            )
            with open(build_sha256_file, "w") as f:
                f.write(current_build_sha256)

            build_dir = f"{os.getcwd()}/{device_config['src']}/build"
            outfile = f"{build_dir}/{device_config['out_file']}"
            if not os.path.exists(outfile):
                raise Exception(f"Failed to find compiled deploy unit: {outfile}")

            filehash = get_sha256_hash(outfile)
            with open(f"{outfile}.sha256", "wb") as f:
                f.write(filehash)

            sign_file(outfile, device_config["sign_key"])
        else:
            log.info(f"{device.id}: No need to compile runtime")


def init_devices(devices):
    """
    Initializes the given devices

    :param list devices: list of devices to initialize
    """

    log.debug(f"Initializing {len(devices)} devices: {[x['id'] for x in devices]}")

    for device_config in devices:
        log.info(f"Initializing device: {device_config['id']}")
        device = Device(device_config)
        device.init()


def update_partial(devices, apps):
    """
    Updates given applications on given devices

    :param list devices: devices to update
    :param list apps: applications to update
    """

    for device_config in devices:
        device = Device(device_config)
        status: deployment_status.Status = device.get_status()

        """
        "   Partial Update
        """
        app_id = "dummy" if device.apps is None else device.apps[0]
        app = next((x for x in apps if x["id"] == app_id), None)

        if app is None:
            log.error(f"App {app_id} not found")
            break

        with open(f"{os.getcwd()}/{app['src']}build/app.wasm.sha256", "rb") as f:
            deployment_sha256 = base64.b64encode(f.read()).decode()

        if status.deployment is None or status.deployment.sha256 != deployment_sha256:
            log.info(f"Updating deployment {app_id} @ {device.id}")
            device.update_partial(app_id, app)
        else:
            log.info(f"Application {app_id} @ {device.id} is up to date")


def update_full(devices):
    """
    Updates the runtime on given devices

    :param list devices: list of devices to update
    """

    for device_config in devices:
        device = Device(device_config)
        status: deployment_status.Status = device.get_status()

        if status.runtime is None:
            log.warning(f"Could not fetch runtime for device {device.id}")
            break

        """
        "   Full Update
        """
        build_dir = f"{os.getcwd()}/{device_config['src']}build/"
        with open(build_dir + device_config["out_file"] + ".sha256", "rb") as f:
            runtime_sha256 = base64.b64encode(f.read()).decode()

        runtime_id = device.id

        log.debug(
            f"{device_config['id']} Runtime SHA256: {status.runtime.sha256} |> {runtime_sha256}"
        )

        if status.runtime.sha256 != runtime_sha256:
            log.info(
                f"Updating runtime for device: {runtime_id} @ {device_config['id']}"
            )
            device.update_full(status.runtime.id, device_config)
        else:
            log.info(f"Runtime @ {runtime_id} is up to date")


def update_devices(devices, apps):
    """
    Combines update_partial and update_full
    """
    update_full(devices)
    update_partial(devices, apps)


def compile_apps(apps):
    """
    Compiles given applications

    :param list apps: list of applications to compile
    """
    for deployment in apps:
        log.info(f"Compiling application: {deployment['id']}")

        exec(
            deployment["build_cmd"],
            f"{os.getcwd()}/{deployment['src']}",
            deployment["properties"],
        )

        filename = f"{os.getcwd()}/{deployment['src']}/{deployment['out_file']}"
        filehash = get_sha256_hash(filename)
        with open(filename + ".sha256", "wb") as f:
            f.write(filehash)
        sign_file(filename, deployment["sign_key"])
