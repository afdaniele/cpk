from cpk.exceptions import CPKException

from cpk.utils.progress_bar import ProgressBar
from ..cli import cpklogger

from ..types import Machine

DEFAULT_TCP_PORT = "2375"
DEFAULT_MACHINE = "unix:///var/run/docker.sock"
DEFAULT_REGISTRY = "docker.io"

DOCKER_INFO = """
Docker Endpoint:
  Machine: {machine}
  Hostname: {Name}
  Operating System: {OperatingSystem}
  Kernel Version: {KernelVersion}
  OSType: {OSType}
  Architecture: {Architecture}
  Total Memory: {MemTotal}
  CPUs: {NCPU}
"""


def push_image(machine: Machine, image: str, progress=True) -> str:
    client = machine.get_client()
    # keep track of total/pushed layers
    layers = set()
    pushed = set()
    pbar = ProgressBar() if progress else None
    final_digest = None
    for line in client.api.push(*image.split(":"), stream=True, decode=True):
        if "error" in line:
            msg = str(line["error"])
            msg = f"Cannot push image {image}:\n{msg}"
            raise CPKException(msg)

        if "aux" in line:
            if "Digest" in line["aux"]:
                final_digest = line["aux"]["Digest"]
                continue

        if "id" not in line:
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
    if final_digest is None:
        msg = "Expected to get final digest, but none arrived "
        cpklogger.warning(msg)
    return final_digest


def transfer_image(origin: Machine, destination: Machine, image, image_size):
    # TODO: re-implement this using in-Python sockets
    # monitor_info = "" if which("pv") else " (install `pv` to see the progress)"
    # cpklogger.info(f'Transferring image "{image}": [{origin}] -> [{destination}]'
    #                f'{monitor_info}...')
    # data_source = ["docker", "-H=%s" % origin, "save", image]
    # data_destination = ["docker", "-H=%s" % destination, "load"]
    # progress_monitor = ["|", "pv", "-cN", "image", "-s", image_size] if which("pv") else []
    # cmd = data_source + progress_monitor + data_destination
    # TODO: re-enable this
    # start_command_in_subprocess(cmd, nostdout=True)
    pass
