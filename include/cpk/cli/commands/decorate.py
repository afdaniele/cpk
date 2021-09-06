import argparse
import os
import re
import subprocess
from shutil import which
from typing import Optional, Callable

import cpk
from cpk.utils.misc import configure_binfmt
from .endpoint import CLIEndpointInfoCommand
from .. import AbstractCLICommand
from ..logger import cpklogger
from ...types import DockerImageName, Machine, Arguments


class CLIDecorateCommand(AbstractCLICommand):
    KEY = 'decorate'

    DOCKER_IMAGE_REGEX = r"^(([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])\.)*" \
                         r"([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])" \
                         r"(:[0-9]+\/)?([0-9a-z-]+[/@]?)([0-9a-z-]+)" \
                         r"[/@]?([0-9a-z-]+)?(:[a-z0-9\.-]+)?$"
    EMAIL_ADDRESS_REGEX = r"^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
    DOCKER_IMAGE_ERROR_MSG = "The pattern must be: [registry/]owner/repository[:tag]"
    EMAIL_ADDRESS_ERROR_MSG = "The pattern must be: 'user@domain.tld'"

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        # ---
        parser.add_argument(
            nargs=1,
            dest="input",
            metavar="INPUT",
            help="The input image",
            type=regex_type(CLIDecorateCommand.DOCKER_IMAGE_REGEX,
                            CLIDecorateCommand.DOCKER_IMAGE_ERROR_MSG)
        )
        parser.add_argument(
            nargs=1,
            dest="output",
            metavar="OUTPUT",
            help="The output image",
            type=regex_type(CLIDecorateCommand.DOCKER_IMAGE_REGEX,
                            CLIDecorateCommand.DOCKER_IMAGE_ERROR_MSG)
        )
        parser.add_argument(
            "-m",
            "--maintainer",
            required=True,
            help="The image maintainer's name",
            type=str
        )
        parser.add_argument(
            "-e",
            "--email",
            default=None,
            help="The image maintainer's email address",
            type=regex_type(CLIDecorateCommand.EMAIL_ADDRESS_REGEX,
                            CLIDecorateCommand.EMAIL_ADDRESS_ERROR_MSG)
        )
        parser.add_argument(
            "--no-multiarch",
            default=False,
            action="store_true",
            help="Whether to disable multiarch support (based on bin_fmt)",
        )
        return parser

    @staticmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        # pick right value of `arch` given endpoint
        if parsed.arch is None:
            cpklogger.info("Parameter `arch` not given, will resolve it from the endpoint.")
            parsed.arch = machine.get_architecture()
            cpklogger.info(f"Parameter `arch` automatically set to `{parsed.arch}`.")

        # parse `input`
        input_image = DockerImageName.from_image_name(parsed.input[0])
        cpklogger.debug(f"+ Input Image:\n{str(input_image)}")

        # parse `output`
        output_image = DockerImageName.from_image_name(parsed.output[0])

        # append arch to the end of the output image
        if output_image.arch is None:
            output_image.arch = parsed.arch
        cpklogger.debug(f"+ Output Image:\n{str(output_image)}")

        # make sure the `docker` CLI tool is installed
        docker_cli = which('docker')
        if docker_cli is None:
            cpklogger.error("The Docker CLI must be installed for this command to work.")
            return False
        cpklogger.debug(f"Docker CLI found at {docker_cli}")

        # find decorator project inside the `cpk` library
        cpk_dir = os.path.dirname(os.path.abspath(cpk.__file__))
        decorator_dir = os.path.join(cpk_dir, "decorator")
        dockerfile = os.path.join(decorator_dir, "Dockerfile")

        # compile maintainer string
        maintainer = f"{parsed.maintainer} ({parsed.email})" if parsed.email else parsed.maintainer

        # get info about docker endpoint
        CLIEndpointInfoCommand.execute(machine, parsed)

        # pick right value of `arch` given endpoint
        machine_arch = machine.get_architecture()
        if parsed.arch is None:
            cpklogger.info("Parameter `arch` not given, will resolve it from the endpoint.")
            parsed.arch = machine_arch
            cpklogger.info(f"Parameter `arch` automatically set to `{parsed.arch}`.")

        # create docker client
        docker = machine.get_client()

        # print info about multiarch
        cpklogger.info("Decorating an image for {} on {}.".format(parsed.arch, machine_arch))
        # - register bin_fmt in the target machine (if needed)
        if not parsed.no_multiarch:
            configure_binfmt(machine_arch, parsed.arch, docker, cpklogger)

        # compile command
        cmd = [
            "docker", "build",
            # TODO: machine is not used here
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
        ]
        cpklogger.info(f"Decorating [{input_image.compile()}] -> [{output_image.compile()}]...")
        cpklogger.debug(f"Running command:\n\t{cmd}")

        # build image
        try:
            subprocess.check_call(cmd)
        except subprocess.SubprocessError as e:
            cpklogger.error(str(e))
            return False

        # success
        cpklogger.info(f"The given image was successfully decorated for CPK.\n"
                       f"Your CPK-compatible image is called\n\n"
                       f"\t\t{output_image.compile()}\n\n"
                       f"You can now use it as a base for your CPK projects and templates.")
        # ---
        return True


def regex_type(pattern: str, error_msg: str) -> Callable[[str], str]:
    def _validator(value: str) -> str:
        if not re.compile(pattern).match(value):
            raise argparse.ArgumentTypeError(f"\n\t{error_msg}")
        return value

    # ---
    return _validator
