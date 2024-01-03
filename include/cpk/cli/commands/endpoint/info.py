import argparse
from typing import Optional

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
        epoint = docker.info()
        epoint['machine'] = machine.name
        if "ServerErrors" in epoint:
            cpklogger.error("\n".join(epoint["ServerErrors"]))
            return False
        epoint["MemTotal"] = human_size(epoint["MemTotal"])
        print(DOCKER_INFO.format(**epoint))
