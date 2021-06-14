import os

import docker
from docker import DockerClient

from cpk.types import Machine


class FromEnvMachine(Machine):

    def __init__(self):
        super(FromEnvMachine, self).__init__("externally-set")

    def get_client(self) -> DockerClient:
        return docker.from_env()


class TCPMachine(Machine):

    def __init__(self, name: str, host: str):
        super(TCPMachine, self).__init__(name, host)

    def get_client(self) -> DockerClient:
        return docker.DockerClient(base_url=self._host)


class UnixSocketMachine(TCPMachine):

    def __init__(self, name: str, host: str = "unix:///var/run/docker.sock"):
        super(UnixSocketMachine, self).__init__(name, host)


class SSHMachine(Machine):

    def __init__(self, name: str, username: str, hostname: str, port: int = 22):
        super(SSHMachine, self).__init__(name)
        self._username = username
        self._hostname = hostname
        self._port = port
        self._host = f"ssh://{self._username}@{self._hostname}:{self._port}"

    def get_client(self) -> DockerClient:
        return docker.DockerClient(base_url=self._host, use_ssh_client=True)
