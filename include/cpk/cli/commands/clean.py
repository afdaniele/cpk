import argparse
from typing import Union

from .. import AbstractCLICommand


class CLICleanCommand(AbstractCLICommand):

    KEY = 'clean'

    @staticmethod
    def parser(parent: Union[None, argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        parser.add_argument(
            "-H",
            "--machine",
            default=None,
            help="Docker socket or hostname to clean up"
        )
        return parser

    @staticmethod
    def execute(parsed: argparse.Namespace) -> bool:
        # TODO
        pass
