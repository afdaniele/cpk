import logging
import os
import shutil
import subprocess
import time
from shutil import which
from typing import Optional, Union

import docker
from cpk.exceptions import CPKException
from docker import DockerClient

from cpk.types import Machine

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from sshconf import empty_ssh_config_file

from cpk.utils.misc import configure_ssh_for_cpk


class FromEnvMachine(Machine):

    def __init__(self):
        super(FromEnvMachine, self).__init__("from-environment")

    @property
    def is_local(self) -> bool:
        return True

    def get_client(self) -> DockerClient:
        return docker.from_env()


class TCPMachine(Machine):
    type: str = "tcp"

    def __init__(self, name: str, host: str):
        super(TCPMachine, self).__init__(name, host)

    @property
    def is_local(self) -> bool:
        hostname, *_ = self._base_url.split(":")
        return hostname in ["tcp://localhost", "tcp://127.0.0.1", "tcp://127.0.1.1"]

    def get_client(self) -> DockerClient:
        try:
            return docker.DockerClient(base_url=self.base_url)
        except docker.errors.DockerException as e:
            raise CPKException(str(e))


class UnixSocketMachine(TCPMachine):
    type: str = "socket"

    def __init__(self, name: str, host: str = "unix:///var/run/docker.sock"):
        super(UnixSocketMachine, self).__init__(name, host)

    @property
    def is_local(self) -> bool:
        return True


class SSHMachine(Machine):
    type: str = "ssh"

    def __init__(self, name: str, user: str, host: str, port: Optional[Union[str, int]] = 22):
        config = {
            "user": user,
            "host": host,
            "port": int(port) if port is not None else 22,
        }
        super(SSHMachine, self).__init__(name, configuration=config)

    @property
    def is_local(self) -> bool:
        return False

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
        return f"{cfg['user']}@{cfg['host']}"

    @property
    def base_url(self) -> Optional[str]:
        return f"ssh://{self.uri}:{self.port}"

    def get_client(self) -> DockerClient:
        return docker.DockerClient(base_url=self.base_url, use_ssh_client=True)

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
        with open(os.open(private_key_fpath, os.O_CREAT | os.O_WRONLY, 0o600), "wb") as fout:
            if logger:
                logger.debug(f"Writing private key to '{private_key_fpath}'")
            fout.write(private_key)
        # - public key
        public_key_fpath = os.path.join(ssh_keys_dir, "id_rsa.pub")
        with open(os.open(public_key_fpath, os.O_CREAT | os.O_WRONLY, 0o644), "wb") as fout:
            if logger:
                logger.debug(f"Writing public key to '{private_key_fpath}'")
            fout.write(public_key)
        # create SSH configuration file
        ssh_conf_fpath = os.path.join(path, "host.conf")
        config = empty_ssh_config_file()
        config.add(
            self.host,
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
        self.remove(logger=logger)
        raise RuntimeError("RSA keys could not be copied to the destination machine.")

    def __enter__(self):
        from cpk import cpkconfig
        # create SSH host configuration file in the SSH pool directory .cpk/ssh
        cpk_ssh_pool_dir = os.path.join(cpkconfig.path, "ssh")
        host_cfg_src_fpath = os.path.join(self.config_path, "host.conf")
        host_cfg_dest_fpath = os.path.join(cpk_ssh_pool_dir, f"{self.name}.conf")
        shutil.copy(host_cfg_src_fpath, host_cfg_dest_fpath)

    def __exit__(self, exc_type, exc_val, exc_tb):
        from cpk import cpkconfig
        # remove SSH host configuration file from the SSH pool directory .cpk/ssh
        cpk_ssh_pool_dir = os.path.join(cpkconfig.path, "ssh")
        host_cfg_fpath = os.path.join(cpk_ssh_pool_dir, f"{self.name}.conf")
        if os.path.exists(host_cfg_fpath) and os.path.isfile(host_cfg_fpath):
            os.remove(host_cfg_fpath)
