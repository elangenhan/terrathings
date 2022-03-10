import itertools
import logging
import sys
import time
from base64 import encode

from paramiko import AutoAddPolicy, SSHClient
from terrathings.connection import ConnectionPlugin, plugins
from terrathings.core.logging import logging as log
from terrathings.core.util import write_device_ip_to_cache

logging.basicConfig()
logging.getLogger("paramiko").setLevel(logging.WARNING)


class SSH(ConnectionPlugin):
    required_properties = [
        {
            "name": "host",
            "type": "string",
            "required": True,
        },
        {
            "name": "username",
            "type": "string",
            "required": True,
        },
        {
            "name": "password",
            "type": "string",
            "required": True,
        },
        {
            "name": "remote_init_command",
            "type": "string",
            "required": True,
        },
    ]

    def __init__(self, properties):
        pass

    def get_deployment(self):
        raise NotImplementedError()

    def initialize_device(self, runtime, device, properties):
        """Initializes the device by copying the tar'ed
        "   deployable to the device, unpacking and
        "   executing the configured command."""
        ssh = self._init_ssh(properties)

        """ Removing current setup and initialize directory """
        self._exec_cmd(ssh, "sudo systemctl stop terrathings")
        self._exec_cmd(
            ssh,
            "sudo rm -rf /opt/terrathings && sudo mkdir -p /opt/terrathings/ && sudo chown -R $USER:$USER /opt/terrathings/ && sleep 1",
        )

        """ Copy runtime to device via sftp """
        sftp = ssh.open_sftp()
        sftp.put(runtime, "/tmp/terrathings.tar.gz")
        sftp.close()

        """ Extract tarball and remove tarball afterwards """
        self._exec_cmd(
            ssh, "sudo tar -xzf /tmp/terrathings.tar.gz -C /opt/terrathings/"
        )
        self._exec_cmd(ssh, "sudo rm -f /tmp/terrathings.tar.gz")

        """ Execute initialization command"""
        remote_init_command = properties.get("remote_init_command", "")
        if remote_init_command:
            log.debug(f"Running init command: {remote_init_command}")
            self._exec_cmd(ssh, remote_init_command)

        """ Write runtime sha256 to file """
        runtime_id = properties.get("runtime_id", "")
        with open(runtime + ".sha256", "rb") as f:
            sha256 = f.read()
            if sha256:
                self._exec_cmd(
                    ssh,
                    f'echo "{sha256.hex()} {runtime_id}" > /opt/terrathings/data/runtime_A.sha256',
                )

        """ Wait for device to be ready """

        def done():
            _, stdout, _ = ssh.exec_command("bash /opt/terrathings/get_status.sh")
            stdout = stdout.readlines()
            return stdout[0].strip("\n") == "true"

        log.info("Waiting for initialization process on device to finish...")
        spinner = itertools.cycle(["-", "/", "|", "\\"])
        while not done():
            sys.stdout.write(next(spinner))
            sys.stdout.flush()
            time.sleep(1)
            sys.stdout.write("\b")

        log.info("Initialization done")

        write_device_ip_to_cache(device.id, properties.get("host"))

        ssh.close()

    def update_full(self):
        raise NotImplementedError()

    def update_partial(self):
        raise NotImplementedError()

    def _init_ssh(self, properties):
        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(
            properties.get("host"),
            username=properties.get("username"),
            password=properties.get("password"),
        )
        return client

    def _exec_cmd(self, client, cmd):
        log.debug(f"SSH: {cmd}")
        _, stdout, _ = client.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            log.warning(f"SSH command failed: {cmd}")
        return stdout


plugins.register(SSH)
