import argparse
from typing import Union

from .. import AbstractCLICommand
from ...types import Machine


class CLICleanCommand(AbstractCLICommand):

    KEY = 'clean'

    @staticmethod
    def parser(parent: Union[None, argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        return parser

    @staticmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        # TODO
        pass
