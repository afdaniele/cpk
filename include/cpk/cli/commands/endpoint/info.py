import argparse
from typing import Optional

from dockertown import SystemInfo

from cpk.cli.utils import combine_args, as_table
from cpk.utils.misc import human_size

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
            "Machine": machine.name,
            "Hostname": epoint_info.name,
            "Operating System": f"{epoint_info.os_type.title()} {epoint_info.operating_system}",
            "Kernel Version": epoint_info.kernel_version,
            "Architecture": epoint_info.architecture,
            "Total Memory": human_size(epoint_info.mem_total),
            "#CPUs": epoint_info.n_cpu,
        }
        print(as_table(epoint, "Docker Endpoint Info"))
        return True
