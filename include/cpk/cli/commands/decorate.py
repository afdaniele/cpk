import argparse
import os
import re
import subprocess
from shutil import which
from typing import Union, Callable

import cpk
from .. import AbstractCLICommand
from ..logger import cpklogger
from ...types import DockerImageName


class CLIDecorateCommand(AbstractCLICommand):
    KEY = 'decorate'

    DOCKER_IMAGE_REGEX = "^((?:(?:[a-z0-9]|[a-z0-9][a-z0-9\\-]*[a-z0-9])\\.)*(?:[a-z0-9]|[a-z0-9][a-z0-9\\-]*[a-z0-9]))(?::([0-9]+)\\/)?(?:[0-9a-z-]+[/@])(?:([0-9a-z-]+))[/@]?(?:([0-9a-z-]+))?(?::[a-z0-9\\.-]+)?$"
    EMAIL_ADDRESS_REGEX = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"

    @staticmethod
    def parser(parent: Union[None, argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        # ---
        parser.add_argument(
            "-i",
            "--input",
            required=True,
            type=regex_type(CLIDecorateCommand.DOCKER_IMAGE_REGEX)
        )
        parser.add_argument(
            "-o",
            "--output",
            required=True,
            type=regex_type(CLIDecorateCommand.DOCKER_IMAGE_REGEX)
        )
        parser.add_argument(
            "-m",
            "--maintainer",
            required=True,
            type=str
        )
        parser.add_argument(
            "-e",
            "--email",
            default=None,
            type=regex_type(CLIDecorateCommand.EMAIL_ADDRESS_REGEX)
        )
        return parser

    @staticmethod
    def execute(parsed: argparse.Namespace) -> bool:
        # parse `input`
        input_image = DockerImageName.from_image_name(parsed.input)
        # parse `output`
        output_image = DockerImageName.from_image_name(parsed.output)
        # make sure the `docker` CLI tool is installed
        if which('docker') is None:
            cpklogger.error("The Docker CLI must be installed for this command to work.")
            return False
        # find decorator project inside the `cpk` library
        cpk_dir = os.path.dirname(os.path.abspath(cpk.__file__))
        decorator_dir = os.path.join(cpk_dir, "decorator")
        dockerfile = os.path.join(decorator_dir, "Dockerfile")
        # compile maintainer string
        maintainer = f"{parsed.maintainer} ({parsed.email})" if parsed.email else parsed.maintainer
        # build image
        subprocess.check_call([
            "docker", "build",
            "-t", output_image.compile(),
            "-f", dockerfile,
            "--build-arg", f"ARCH={parsed.arch}",
            "--build-arg", f"BASE_REGISTRY={input_image.registry.compile(allow_defaults=True)}",
            "--build-arg", f"BASE_ORGANIZATION={input_image.user}",
            "--build-arg", f"BASE_REPOSITORY={input_image.repository}",
            "--build-arg", f"BASE_TAG={input_image.tag}",
            "--build-arg", f"ORGANIZATION={output_image.user}",
            "--build-arg", f"NAME={output_image.repository}",
            "--build-arg", f"MAINTAINER={maintainer}",
            "--build-arg", f"CPK_VERSION={cpk.__version__}",
            decorator_dir
        ])
        # ---
        return True


def regex_type(pattern: str) -> Callable[[str], str]:
    def _validator(value: str) -> str:
        if not re.compile(pattern).match(value):
            raise argparse.ArgumentTypeError
        return value

    # ---
    return _validator
