import argparse
from typing import Optional, Dict, Type

from cpk.cli import AbstractCLICommand
from cpk.cli.commands.machine.create import CLIMachineCreateCommand
from cpk.cli.commands.machine.info import CLIMachineInfoCommand
from cpk.cli.commands.machine.list import CLIMachineListCommand
from cpk.cli.commands.machine.remove import CLIMachineRemoveCommand
from cpk.types import Machine, Arguments

_supported_subcommands: Dict[str, Type[AbstractCLICommand]] = {
    "create": CLIMachineCreateCommand,
    "info": CLIMachineInfoCommand,
    "rm": CLIMachineRemoveCommand,
    "remove": CLIMachineRemoveCommand,
    "ls": CLIMachineListCommand,
    "list": CLIMachineListCommand,
}


class CLIMachineCommand(AbstractCLICommand):

    KEY = 'machine'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        # create a temporary parser used to select the subcommand
        parser = argparse.ArgumentParser(parents=[parent], prog='cpk machine')
        parser.add_argument(
            'subcommand',
            choices=_supported_subcommands.keys(),
            help=f"Subcommand. Can be any of {', '.join(_supported_subcommands.keys())}"
        )
        parsed, _ = parser.parse_known_args(args)
        # return subcommand's parser
        subcommand = _supported_subcommands[parsed.subcommand]
        return subcommand.parser(parser, args)

    @staticmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        subcommand = _supported_subcommands[parsed.subcommand]
        return subcommand.execute(machine, parsed)
