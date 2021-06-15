import argparse
from typing import Optional

from cpk import cpkconfig
from cpk.cli import AbstractCLICommand, cpklogger
from cpk.types import Machine, Arguments


class CLIMachineInfoCommand(AbstractCLICommand):

    KEY = 'machine info'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)
        parser.add_argument(
            'name',
            type=str,
            help="Name of the machine"
        )
        # ---
        return parser

    @staticmethod
    def execute(_: Machine, parsed: argparse.Namespace) -> bool:
        # make sure the machine exists
        if parsed.name not in cpkconfig.machines:
            cpklogger.error(f"The machine '{parsed.name}' does not exist.")
            return False
        print(cpkconfig.machines[parsed.name])
