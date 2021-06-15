import argparse
import logging
import os
from abc import abstractmethod, ABC
from typing import Optional, Type

from cpk.cli.logger import cpklogger
from cpk.constants import CANONICAL_ARCH
from cpk.types import Machine, Arguments


class AbstractCLICommand(ABC):

    KEY = None

    @classmethod
    def name(cls) -> str:
        return cls.KEY

    @staticmethod
    def common_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "-C",
            "--workdir",
            default=os.getcwd(),
            help="Directory containing the CPK project"
        )
        parser.add_argument(
            "-H",
            "--machine",
            default=None,
            help="CPK machine or endpoint hostname where to perform the action"
        )
        parser.add_argument(
            "-a",
            "--arch",
            default=None,
            choices=set(CANONICAL_ARCH.values()),
            help="Target architecture for the image",
        )
        parser.add_argument(
            "-f",
            "--force",
            default=False,
            action="store_true",
            help="Whether to force the action",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            default=False,
            action="store_true",
            help="Be verbose"
        )
        parser.add_argument(
            "--debug",
            default=False,
            action="store_true",
            help="Enable debug mode"
        )
        return parser

    @classmethod
    def get_parser(cls, args: Arguments) -> argparse.ArgumentParser:
        common_parser = cls.common_parser()
        command_parser = cls.parser(common_parser, args)
        command_parser.prog = f'cpk {cls.KEY}'
        return command_parser

    @staticmethod
    @abstractmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        pass

    @staticmethod
    @abstractmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        pass


class CPKCLI:

    @staticmethod
    def parse_arguments(command: Type[AbstractCLICommand], args: Arguments) -> argparse.Namespace:
        parser = command.get_parser(args)
        parsed = parser.parse_args(args)
        # sanitize workdir
        parsed.workdir = os.path.abspath(parsed.workdir)
        # enable debug
        if parsed.debug:
            cpklogger.setLevel(logging.DEBUG)
        # ---
        return parsed


__all__ = [
    "AbstractCLICommand",
    "CPKCLI",
    "cpklogger"
]
