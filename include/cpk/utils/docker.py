from cpk.exceptions import CPKException

from cpk.utils.progress_bar import ProgressBar
from ..cli import cpklogger

from ..types import CPKMachine

DEFAULT_TCP_PORT = "2375"
DEFAULT_MACHINE = "unix:///var/run/docker.sock"

w = "\033[37m"
x = "\033[0m"

DOCKER_INFO = f"""
------- Docker Endpoint Info --------
  {w}Machine:{x} {{machine}}
  {w}Hostname:{x} {{Name}}
  {w}Operating System:{x} {{OperatingSystem}}
  {w}Kernel Version:{x} {{KernelVersion}}
  {w}OSType:{x} {{OSType}}
  {w}Architecture:{x} {{Architecture}}
  {w}Total Memory:{x} {{MemTotal}}
  {w}CPUs:{x} {{NCPU}}
------------------------------------
"""


def push_image(machine: CPKMachine, image: str, progress=True) -> str:
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
