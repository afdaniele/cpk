import argparse
from typing import Optional

from cpk import cpkconfig
from cpk.cli import AbstractCLICommand, cpklogger
from cpk.types import Machine, Arguments
from cpk.utils.misc import ask_confirmation


class CLIMachineRemoveCommand(AbstractCLICommand):

    KEY = 'machine remove'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)
        parser.add_argument(
            'name',
            type=str,
            help="Name of the machine to remove"
        )
        # ---
        return parser

    @staticmethod
    def execute(_: Machine, parsed: argparse.Namespace) -> bool:
        # make sure the machine exists
        if parsed.name not in cpkconfig.machines:
            cpklogger.error(f"The machine '{parsed.name}' does not exist.")
            return False
        # get machine
        machine = cpkconfig.machines[parsed.name]
        # show some info
        cpklogger.info("The following machine will be deleted.")
        print(machine)
        # ask for confirmation
        granted = ask_confirmation(
            cpklogger,
            message=f"The machine '{parsed.name}' will be deleted. This cannot be undone.",
            default='n'
        )
        if not granted:
            raise KeyboardInterrupt()
        # remove machine
        machine.remove(cpklogger)
        cpklogger.info("Machine deleted.")
