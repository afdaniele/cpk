import argparse
from typing import Optional

from cpk.cli.commands.info import CLIInfoCommand

from cpk import CPKProject

from .. import AbstractCLICommand, cpklogger
from ...types import Machine, Arguments


class CLICleanCommand(AbstractCLICommand):

    KEY = 'clean'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        return parser

    @staticmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        # get project
        project = CPKProject(parsed.workdir, parsed=parsed)

        # show info about project
        CLIInfoCommand.execute(machine, parsed)

        # pick right value of `arch` given endpoint
        if parsed.arch is None:
            cpklogger.info("Parameter `arch` not given, will resolve it from the endpoint.")
            parsed.arch = machine.get_architecture()
            cpklogger.info(f"Parameter `arch` automatically set to `{parsed.arch}`.")

        # create docker client
        docker = machine.get_client()

        # TODO: perform clean

        return True
