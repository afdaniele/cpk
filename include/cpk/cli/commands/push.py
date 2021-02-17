import argparse
from typing import Union

from .. import AbstractCLICommand


class CLIPushCommand(AbstractCLICommand):

    KEY = 'push'

    @staticmethod
    def parser(parent: Union[None, argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        parser.add_argument(
            "--rm",
            default=False,
            action="store_true",
            help="Remove the images once the build is finished",
        )
        return parser

    @staticmethod
    def execute(parsed: argparse.Namespace) -> bool:
        # TODO
        pass
