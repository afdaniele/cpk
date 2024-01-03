import argparse
from typing import Optional

from dockertown import SystemInfo

from cpk.cli.utils import combine_args
from cpk.utils.misc import human_size

from cpk.utils.docker import DOCKER_INFO

from cpk.cli import AbstractCLICommand, cpklogger
from cpk.types import CPKMachine, Arguments


class CLIEndpointInfoCommand(AbstractCLICommand):

    KEY = 'endpoint info'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)
        # ---
        return parser

    @staticmethod
    def execute(machine: CPKMachine, parsed: argparse.Namespace, **kwargs) -> bool:
        # combine arguments
        parsed = combine_args(parsed, kwargs)
        # ---
        # create docker client
        docker = machine.get_client()
        # get info about docker endpoint
        if not parsed.quiet:
            cpklogger.info("Retrieving info about Docker endpoint...")
        # ---
        epoint_info: SystemInfo = docker.info()
        epoint: dict = {
            "machine": machine.name,
            "name": epoint_info.name,
            "os": epoint_info.operating_system,
            "kernel": epoint_info.kernel_version,
            "os_type": epoint_info.os_type,
            "arch": epoint_info.architecture,
            "memory_total": human_size(epoint_info.mem_total),
            "ncpus": epoint_info.n_cpu,
        }
        print(DOCKER_INFO.format(**epoint))
        return True
