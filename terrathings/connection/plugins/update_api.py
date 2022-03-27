import json
import os
import time

import requests
from terrathings.connection import (
    ConnectionPlugin,
    Deployment,
    Runtime,
    Status,
    plugins,
)
from terrathings.core.logging import logging as log
from terrathings.core.util import read_device_ip_from_cache


class UpdateAPI(ConnectionPlugin):
    """Host is not required, because it can also be fetched from cache"""

    required_properties = [
        {"name": "host", "type": "string", "required": False},
        {"name": "port", "type": "int", "required": False},
    ]

    def __init__(self, properties):
        pass

    def get_deployment(self, device, properties):
        """Reads device ip from config, if not found, reads it from cache"""
        host = properties.get("host", None)
        if host is None:
            log.debug(f"No host for device {device.id} found, using cache")
            host = read_device_ip_from_cache(device.id)

        if host is None:
            raise Exception(f"No ip for device {device.id} found")

        port = properties.get("port", 80)
        baseurl = f"http://{host}:{port}"

        deployment = None
        runtime = None
        try:
            r = requests.get(f"{baseurl}/status")
            data = r.json()

            if runtime_data := data["runtime"]:
                runtime = Runtime(id=runtime_data["id"], sha256=runtime_data["sha256"])

            if deployment_data := data["deployment"]:
                deployment = Deployment(
                    id=deployment_data["id"], sha256=deployment_data["sha256"]
                )

        except Exception as e:
            log.warning(e)
        return Status(
            deployment=deployment,
            runtime=runtime,
        )

    def initialize_device(self):
        raise NotImplementedError()

    def update_full(self, runtime, device, properties):
        """upload runtime via http"""

        files = {"runtime.tar.gz": open(f"{os.getcwd()}/{runtime}", "rb")}
        signature = (
            open(f"{os.getcwd()}/{runtime}.sha256.signed", "rb").read().decode("utf-8")
        )

        """ Reads device ip from config, if not found, reads it from cache """
        host = properties.get("host", None)
        if host is None:
            log.debug(f"No host for device {device.id} found, using cache")
            host = read_device_ip_from_cache(device.id)

        if host is None:
            raise Exception(f"No ip for device {device.id} found")

        port = properties.get("port", 80)
        baseurl = f"http://{host}:{port}"

        try:
            log.debug(
                f"Calling {baseurl}/update?type=full&signature={signature}&runtime_id={device.runtime}",
            )
            r = requests.post(
                f"{baseurl}/update?type=full&signature={signature}&runtime_id={device.runtime}",
                files=files,
            )

            if r.status_code != 200:
                raise Exception(r.text)
        except Exception as e:
            log.warning(e)
            return

        log.info(f"Waiting for runtime {device.id} to initialize")
        retries = 30
        while True:
            retries -= 1
            try:
                r = requests.get(f"{baseurl}/status", timeout=2)
                data = r.json()
                log.debug(f"Status response: {data}")
                if data["runtime"] or retries < 0:
                    break
            except Exception as e:
                log.debug("Connection failed - retrying in 5 seconds...")
                time.sleep(5)

    def update_partial(self, app, device, properties):
        """upload deployment via http"""
        files = {"app.wasm": open(f"{os.getcwd()}/{app}", "rb")}
        signature = (
            open(f"{os.getcwd()}/{app}.sha256.signed", "rb").read().decode("utf-8")
        )

        deployment_id = app.split("/")[-1].split(".")[0]

        """ Reads device ip from config, if not found, reads it from cache """
        host = properties.get("host", None)
        if host is None:
            log.debug(f"No host for device {device.id} found, using cache")
            host = read_device_ip_from_cache(device.id)

        if host is None:
            raise Exception(f"No ip for device {device.id} found")

        port = properties.get("port", 80)
        baseurl = f"http://{host}:{port}"

        r = requests.post(
            f"{baseurl}/update?type=partial&signature={signature}&deployment_id={deployment_id}",
            files=files,
        )
        if r and r.text:
            log.info(r.text)


plugins.register(UpdateAPI)
