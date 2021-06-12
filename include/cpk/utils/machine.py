import argparse
from typing import Optional, List

from docker import DockerClient

from cpk.machine import UnixSocketMachine, Machine, TCPMachine


def load_machines() -> List[Machine]:
    # TODO: implement
    return []


def get_machine(parsed: argparse.Namespace) -> Machine:
    if parsed.machine is None:
        return UnixSocketMachine("default")
    # get all CPK machines
    cpk_machines = load_machines()
    # match machine names against given string
    for machine in cpk_machines:
        if machine.name == str(parsed.machine).strip():
            return machine
    # assume it is a hostname or IP address
    return TCPMachine(parsed.machine, parsed.machine)


