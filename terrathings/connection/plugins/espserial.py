import json
import os
import subprocess

import docker
import serial
from terrathings.connection import (
    ConnectionPlugin,
    Deployment,
    Runtime,
    Status,
    plugins,
)
from terrathings.core.logging import logging as log
from terrathings.core.util import write_device_ip_to_cache


class ESPSerial(ConnectionPlugin):
    required_properties = [
        {"name": "device", "type": "string", "required": True},
        {"name": "baudrate", "type": "number", "required": True},
    ]

    def __init__(self, properties):
        pass

    def get_deployment(self, device, properties):
        serial_data = self._read_serial()
        ip = serial_data["ip"]
        write_device_ip_to_cache(device.id, ip)

        return Status(
            deployment=Deployment(version="1.0.0"),
            runtime=Runtime(version="1.0.0"),
        )

    def initialize_device(self, runtime, device, properties):
        src_dir = device.src
        device_id = device.id
        cmd = properties.get("cmd", "")
        env = device.properties

        runtime_id = runtime.split("/")[-1]
        runtime_sha256 = ""
        with open(f"{os.getcwd()}/{src_dir}build/firmware.bin.sha256", "rb") as f:
            runtime_sha256 = f.read()

        p = subprocess.Popen(
            cmd,
            shell=True,
            cwd=f"{os.getcwd()}/{src_dir}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ.copy(), **env, runtime_id: runtime_id},
        )
        for line in p.stdout:
            log.debug(line.decode("utf-8"))

        serial_data = self._read_serial()
        ip = serial_data["ip"]

        write_device_ip_to_cache(device_id, ip)
        return Status(runtime=None, deployment=None)

    def update_full(self):
        self._execute_docker()

    def _read_serial(self):
        ser = serial.Serial(
            "/dev/ttyUSB0",
            115200,
            timeout=2,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        ser.flushInput()
        ser.flushOutput()
        while True:
            ser.write(b"\n")
            data = ser.readline().decode("utf-8")
            print(data)
            try:
                data = json.loads(data)
                return data
            except:
                log.debug(f"ESPSerial Error: {data}")

    def _flash_with_pio(self):
        # PATH=$PATH:~/.platformio/penv/bin
        p = subprocess.Popen(
            "docker run --rm --mount type=bind,source=$(pwd),target=/workspace -u $(id -u $USER):$(id -g $USER) sglahn/platformio-core:latest run",
            shell=True,
            cwd=f"{os.getcwd()}/templates/devices/esp32",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
        )
        for line in p.stdout:
            log.info(line.decode("utf-8"))

    def _execute_docker(self):
        client = docker.from_env()
        c = client.containers.run(
            "espressif/idf",
            "idf.py build flash",
            working_dir="/workdir",
            devices=[f"{self.device}:/dev/ttyUSB0:rwm"],
            volumes={
                f"{os.getcwd()}/templates/devices/esp32": {
                    "bind": "/workdir",
                    "mode": "rw",
                }
            },
            auto_remove=True,
        )

        log.info(c.decode("utf-8"))

    def update_partial(self):
        raise NotImplementedError()


plugins.register(ESPSerial)
