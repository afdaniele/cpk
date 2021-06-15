import logging
import os
import subprocess
import time
from shutil import which
from typing import Optional

import docker
from docker import DockerClient

from cpk.types import Machine

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from sshconf import empty_ssh_config_file

from cpk.utils.misc import configure_ssh_for_cpk


class FromEnvMachine(Machine):

    def __init__(self):
        super(FromEnvMachine, self).__init__("externally-set")

    def get_client(self) -> DockerClient:
        return docker.from_env()


class TCPMachine(Machine):
    type: str = "tcp"

    def __init__(self, name: str, host: str):
        super(TCPMachine, self).__init__(name, host)

    def get_client(self) -> DockerClient:
        return docker.DockerClient(base_url=self._base_url)


class UnixSocketMachine(TCPMachine):
    type: str = "socket"

    def __init__(self, name: str, host: str = "unix:///var/run/docker.sock"):
        super(UnixSocketMachine, self).__init__(name, host)


class SSHMachine(Machine):
    type: str = "ssh"

    def __init__(self, name: str, user: str, host: str, port: int = 22):
        config = {
            "user": user,
            "host": host,
            "port": port,
        }
        super(SSHMachine, self).__init__(name, configuration=config)

    @property
    def user(self) -> str:
        return self._configuration["user"]

    @property
    def host(self) -> str:
        return self._configuration["host"]

    @property
    def port(self) -> Optional[int]:
        return self._configuration["port"]

    @property
    def uri(self) -> Optional[str]:
        cfg = self._configuration
        return f"{cfg['user']}@{cfg['host']}" + (f":{cfg['port']}" if cfg['port'] else "")

    @property
    def base_url(self) -> Optional[str]:
        return f"ssh://{self.uri}"

    def get_client(self) -> DockerClient:
        return docker.DockerClient(base_url=self._base_url, use_ssh_client=True)

    def save(self, logger: Optional[logging.Logger] = None):
        from cpk import cpkconfig
        path = os.path.join(cpkconfig.path, "machines", self.name)
        # make sure the tool `ssh-copy-id` is present
        ssh_copy_id = which("ssh-copy-id")
        if ssh_copy_id is None:
            raise ValueError("The SSH command 'ssh-copy-id' is required.")
        if logger:
            logger.debug(f"Tool 'ssh-copy-id' found at '{ssh_copy_id}'")
        # store machine descriptor
        super(SSHMachine, self).save()
        # create keys
        key = rsa.generate_private_key(
            backend=crypto_default_backend(),
            public_exponent=65537,
            key_size=2048
        )
        # noinspection PyTypeChecker
        private_key = key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            crypto_serialization.NoEncryption()
        )
        # noinspection PyTypeChecker
        public_key = key.public_key().public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH
        )
        # save keys
        ssh_keys_dir = os.path.join(path, "keys")
        if logger:
            logger.debug(f"Creating keys directory '{ssh_keys_dir}'")
        os.makedirs(ssh_keys_dir, mode=0o700, exist_ok=True)
        # - private key
        private_key_fpath = os.path.join(ssh_keys_dir, "id_rsa")
        with open(private_key_fpath, "wb") as fout:
            if logger:
                logger.debug(f"Writing private key to '{private_key_fpath}'")
            fout.write(private_key)
        # - public key
        public_key_fpath = os.path.join(ssh_keys_dir, "id_rsa.pub")
        with open(public_key_fpath, "wb") as fout:
            if logger:
                logger.debug(f"Writing public key to '{private_key_fpath}'")
            fout.write(public_key)
        # create SSH configuration file
        ssh_conf_fpath = os.path.join(path, "ssh.conf")
        config = empty_ssh_config_file()
        config.add(
            self.name,
            Hostname=self.host,
            User=self.user,
            **({"Port": self.port} if self.port else {}),
            IdentityFile=private_key_fpath
        )
        if logger:
            logger.debug(f"Writing SSH host configuration to '{ssh_conf_fpath}'")
        config.write(ssh_conf_fpath)
        # configure user's environment for cpk
        configure_ssh_for_cpk(logger)
        # try to transfer the keys to the machine
        cmd = ["ssh-copy-id", "-i", private_key_fpath, self.uri]
        if logger:
            logger.debug(f"Running $> '{str(cmd)}'")
            logger.info("The newly created RSA key will be copied to the destination machine.")
            logger.info("Enter the SSH password when prompted:")
            time.sleep(0.5)
        retcode = subprocess.call(cmd, stderr=subprocess.DEVNULL)
        if retcode == 0:
            return
        raise RuntimeError("RSA keys could not be copied to the destination machine.")