import os
import docker
from typing import Union
from docker.errors import ImageNotFound

from cpk.constants import CANONICAL_ARCH

from .progress_bar import ProgressBar
from ..exceptions import CPKException

DEFAULT_TCP_PORT = "2375"
DEFAULT_MACHINE = "unix:///var/run/docker.sock"
DEFAULT_REGISTRY = "docker.io"

DOCKER_INFO = """
Docker Endpoint:
  Hostname: {Name}
  Operating System: {OperatingSystem}
  Kernel Version: {KernelVersion}
  OSType: {OSType}
  Architecture: {Architecture}
  Total Memory: {MemTotal}
  CPUs: {NCPU}
"""


# def sanitize_docker_baseurl(baseurl: str, port=DEFAULT_TCP_PORT):
#     if baseurl.startswith("unix:"):
#         return baseurl
#     elif baseurl.startswith("tcp://"):
#         return baseurl
#     else:
#         return f"tcp://{baseurl}:{port}"


# def get_client(endpoint: Union[None, str, docker.DockerClient] = None) -> docker.DockerClient:
#     if endpoint is None:
#         client = docker.from_env()
#     else:
#         # create client
#         client = endpoint if isinstance(endpoint, docker.DockerClient) \
#             else docker.DockerClient(base_url=sanitize_docker_baseurl(endpoint))
#     # (try to) login
#     # noinspection PyBroadException
#     try:
#         login_client(client)
#     except BaseException:
#         pass
#     # ---
#     return client





# def pull_if_not_exist(image, endpoint=None, progress=True):
#     client = get_client(endpoint)
#     try:
#         client.images.get(image)
#     except ImageNotFound:
#         pull_image(image, endpoint, progress)

# def parse_configurations(config_file: str) -> dict:
#     with open(config_file, "rt") as fin:
#         configurations_content = yaml.load(fin, Loader=yaml.SafeLoader)
#     if "version" not in configurations_content:
#         raise ValueError("The configurations file must have a root key 'version'.")
#     if configurations_content["version"] == "1.0":
#         return configurations_content["configurations"]


# def docker_client(endpoint):
#     return (
#         endpoint
#         if isinstance(endpoint, docker.DockerClient)
#         else docker.DockerClient(base_url=sanitize_docker_baseurl(endpoint))
#     )
