import argparse
from typing import Optional

from .. import AbstractCLICommand
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
        # TODO
        pass
