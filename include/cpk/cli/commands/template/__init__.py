import argparse
from typing import Optional, Dict, Type

from ....cli import AbstractCLICommand
from ....types import CPKMachine, Arguments
from ...utils import hide_argument
from .apply import CLITemplateApplyCommand
from .diff import CLITemplateDiffCommand

_supported_subcommands: Dict[str, Type[AbstractCLICommand]] = {
    "diff": CLITemplateDiffCommand,
    "apply": CLITemplateApplyCommand,
}


class CLITemplateCommand(AbstractCLICommand):

    KEY = 'template'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        # remove options that are not needed
        if parent:
            hide_argument(parent, "machine")
            hide_argument(parent, "arch")
        # create a temporary parser used to select the subcommand
        parser = argparse.ArgumentParser(parents=[parent], prog='cpk template')
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
    def execute(machine: CPKMachine, parsed: argparse.Namespace) -> bool:
        subcommand = _supported_subcommands[parsed.subcommand]
        return subcommand.execute(machine, parsed)
