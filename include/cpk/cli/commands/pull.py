import argparse
from typing import Optional

from docker.errors import APIError

from .endpoint import CLIEndpointInfoCommand
from .info import CLIInfoCommand
from .. import AbstractCLICommand, cpklogger
from ... import CPKProject
from ...exceptions import CPKProjectPullException
from ...types import Machine, Arguments


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
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        # get project
        project = CPKProject(parsed.workdir, parsed=parsed)

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
        images = [project.image(parsed.arch)]

        # release image
        if parsed.release and project.is_release():
            images += [project.image_release(parsed.arch)]

        for image in images:
            # print info about registry
            msg = "Pulling image {} to {}.".format(image, project.registry)
            cpklogger.info(msg)
            # pull image
            try:
                machine.pull_image(image, progress=True)
            except APIError as e:
                cpklogger.error(f"An error occurred while pulling the project image:\n{str(e)}")
                return False
            except CPKProjectPullException:
                cpklogger.error(f"An error occurred while pulling the project image.")
                return False

        cpklogger.info("Image pulled successfully!")
