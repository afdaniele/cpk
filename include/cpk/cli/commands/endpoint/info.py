import argparse
from typing import Optional

from cpk.utils.misc import human_size

from cpk.utils.docker import DOCKER_INFO

from cpk.cli import AbstractCLICommand, cpklogger
from cpk.types import Machine, Arguments


class CLIEndpointInfoCommand(AbstractCLICommand):

    KEY = 'endpoint info'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)
        # ---
        return parser

    @staticmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        # create docker client
        docker = machine.get_client()

        # get info about docker endpoint
        cpklogger.info("Retrieving info about Docker endpoint...")
        epoint = docker.info()
        epoint['machine'] = machine.name
        if "ServerErrors" in epoint:
            cpklogger.error("\n".join(epoint["ServerErrors"]))
            return False
        epoint["MemTotal"] = human_size(epoint["MemTotal"])
        cpklogger.print(DOCKER_INFO.format(**epoint))
