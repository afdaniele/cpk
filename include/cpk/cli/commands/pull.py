import argparse
from typing import Optional, List

import dockertown.exceptions

from .endpoint import CLIEndpointInfoCommand
from .info import CLIInfoCommand
from .. import AbstractCLICommand, cpklogger
from ..utils import combine_args
from ... import CPKProject
from ...exceptions import CPKProjectPullException
from ...types import CPKMachine, Arguments


class CLIPullCommand(AbstractCLICommand):

    KEY = 'pull'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        parser.add_argument(
            "--tag",
            default=None,
            type=str,
            help="Custom tag"
        )
        parser.add_argument(
            "--release",
            default=False,
            action="store_true",
            help="Pull release image as well",
        )
        return parser

    @staticmethod
    def execute(machine: CPKMachine, parsed: argparse.Namespace, **kwargs) -> bool:
        # combine arguments
        parsed = combine_args(parsed, kwargs)
        # ---
        # get project
        project = CPKProject(parsed.workdir)

        # show info about project
        CLIInfoCommand.execute(machine, parsed)

        # get info about docker endpoint
        CLIEndpointInfoCommand.execute(machine, parsed)

        # pick right value of `arch` given endpoint
        if parsed.arch is None:
            cpklogger.info("Parameter `arch` not given, will resolve it from the endpoint.")
            parsed.arch = machine.get_architecture()
            cpklogger.info(f"Parameter `arch` automatically set to `{parsed.arch}`.")

        # create defaults
        images: List[str] = [
            project.docker.image.name(parsed.arch).compile()
        ]

        # release image
        if parsed.release and project.is_release():
            images += [
                project.docker.image.release_name(parsed.arch).compile()
            ]

        for image in images:
            # print info about registry
            msg = "Pulling image {} from {}.".format(image, project.docker.registry.compile(True))
            cpklogger.info(msg)
            # pull image
            try:
                machine.pull_image(image, progress=True)
            except dockertown.exceptions.DockerException as e:
                cpklogger.error(f"An error occurred while pulling the project image:\n{str(e)}")
                return False
            except CPKProjectPullException:
                cpklogger.error(f"An error occurred while pulling the project image.")
                return False

        cpklogger.info("Image pulled successfully!")
