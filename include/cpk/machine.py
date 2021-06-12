from cpk.types import Machine


class UnixSocketMachine(Machine):

    def __init__(self, name: str, host: str = "unix:///var/run/docker.sock"):
        super(UnixSocketMachine, self).__init__(name)
        self._host = host

    def get_host_string(self) -> str:
        return self._host


class TCPMachine(Machine):

    def __init__(self, name: str, host: str):
        super(TCPMachine, self).__init__(name)
        self._host = host

    def get_host_string(self) -> str:
        return self._host


class SSHMachine(Machine):

    def __init__(self, name: str, username: str, hostname: str, port: int = 22):
        super(SSHMachine, self).__init__(name)
        self._username = username
        self._hostname = hostname
        self._port = port

    def get_host_string(self) -> str:
        return f"{self._username}@{self._hostname}:{self._port}"
