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


def get_endpoint_ncpus(endpoint: Union[None, str, docker.DockerClient] = None) -> Union[int, None]:
    client = get_client(endpoint)
    # ---
    # noinspection PyBroadException
    try:
        endpoint_ncpus = client.info()["NCPU"]
    except BaseException:
        return None
    return endpoint_ncpus


def get_endpoint_architecture(endpoint: Union[None, str, docker.DockerClient] = None):
    client = get_client(endpoint)
    # ---
    endpoint_arch = client.info()["Architecture"]
    if endpoint_arch not in CANONICAL_ARCH:
        raise CPKException(f"Unsupported architecture '{endpoint_arch}'.")
    return CANONICAL_ARCH[endpoint_arch]


def sanitize_docker_baseurl(baseurl: str, port=DEFAULT_TCP_PORT):
    if baseurl.startswith("unix:"):
        return baseurl
    elif baseurl.startswith("tcp://"):
        return baseurl
    else:
        return f"tcp://{baseurl}:{port}"


def get_client(endpoint: Union[None, str, docker.DockerClient] = None) -> docker.DockerClient:
    if endpoint is None:
        client = docker.from_env()
    else:
        # create client
        client = endpoint if isinstance(endpoint, docker.DockerClient) \
            else docker.DockerClient(base_url=sanitize_docker_baseurl(endpoint))
    # (try to) login
    # noinspection PyBroadException
    try:
        login_client(client)
    except BaseException:
        pass
    # ---
    return client


def login_client(client):
    username = os.environ.get('DOCKER_USERNAME', None)
    password = os.environ.get('DOCKER_PASSWORD', None)
    if username is not None and password is not None:
        client.login(username=username, password=password)


def pull_image(image, endpoint=None, progress=True) -> bool:
    client = get_client(endpoint)
    layers = set()
    pulled = set()
    pbar = ProgressBar() if progress else None
    for line in client.api.pull(image, stream=True, decode=True):
        if "id" not in line or "status" not in line:
            continue
        layer_id = line["id"]
        layers.add(layer_id)
        if line["status"] in ["Already exists", "Pull complete"]:
            pulled.add(layer_id)
        # update progress bar
        if progress:
            percentage = max(0.0, min(1.0, len(pulled) / max(1.0, len(layers)))) * 100.0
            pbar.update(percentage)
    if progress:
        pbar.done()
    return True


def push_image(image, endpoint=None, progress=True, **kwargs):
    client = get_client(endpoint)
    layers = set()
    pushed = set()
    pbar = ProgressBar() if progress else None
    for line in client.api.push(*image.split(":"), stream=True, decode=True, **kwargs):
        if "id" not in line or "status" not in line:
            continue
        layer_id = line["id"]
        layers.add(layer_id)
        if line["status"] in ["Layer already exists", "Pushed"]:
            pushed.add(layer_id)
        # update progress bar
        if progress:
            percentage = max(0.0, min(1.0, len(pushed) / max(1.0, len(layers)))) * 100.0
            pbar.update(percentage)
    if progress:
        pbar.done()


def pull_if_not_exist(image, endpoint=None, progress=True):
    client = get_client(endpoint)
    try:
        client.images.get(image)
    except ImageNotFound:
        pull_image(image, endpoint, progress)

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
