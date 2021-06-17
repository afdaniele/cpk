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
