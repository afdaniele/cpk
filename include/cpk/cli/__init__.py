import argparse
import logging
import os
from abc import abstractmethod, ABC
from typing import Union

from cpk.cli.logger import cpklogger
from cpk.constants import CANONICAL_ARCH
from cpk.utils.docker import get_client, get_endpoint_architecture


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
            help="Docker socket or hostname where to perform the action"
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
    def get_parser(cls) -> argparse.ArgumentParser:
        common_parser = cls.common_parser()
        command_parser = cls.parser(common_parser)
        command_parser.prog = f'cpk {cls.KEY}'
        return command_parser

    @classmethod
    def parse_arguments(cls, args) -> argparse.Namespace:
        parser = cls.get_parser()
        parsed = parser.parse_args(args)
        # sanitize workdir
        parsed.workdir = os.path.abspath(parsed.workdir)
        # pick right value of `arch` given endpoint
        if parsed.arch is None:
            cpklogger.info("Parameter `arch` not given, will resolve it from the endpoint.")
            docker = get_client(endpoint=parsed.machine)
            parsed.arch = get_endpoint_architecture(docker)
            cpklogger.info(f"Parameter `arch` automatically set to `{parsed.arch}`.")

        # enable debug
        if parsed.debug:
            cpklogger.setLevel(logging.DEBUG)
        # ---
        return parsed

    @staticmethod
    @abstractmethod
    def parser(parent: Union[None, argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
        pass

    @staticmethod
    @abstractmethod
    def execute(parsed: argparse.Namespace) -> bool:
        pass


__all__ = [
    "AbstractCLICommand"
]