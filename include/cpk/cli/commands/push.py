import argparse
from typing import Optional, List

from .endpoint import CLIEndpointInfoCommand
from .info import CLIInfoCommand
from .. import AbstractCLICommand, cpklogger
from ..utils import combine_args
from ... import CPKProject
from ...exceptions import CPKProjectPushException
from ...types import CPKMachine, Arguments
from ...utils.cli import check_git_status
from ...utils.docker import push_image


class CLIPushCommand(AbstractCLICommand):

    KEY = 'push'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        parser.add_argument(
            "--rm",
            default=False,
            action="store_true",
            help="Remove the images once the build is finished",
        )
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
            help="Push release image as well",
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

        # check git workspace status
        proceed = check_git_status(project, parsed)
        if not proceed:
            return False

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
            msg = "Pushing image {} to {}.".format(image, project.docker.registry.compile(True))
            cpklogger.info(msg)
            # push image
            try:
                push_image(machine, image, progress=True)
            except APIError as e:
                cpklogger.error(f"An error occurred while pushing the project image:\n{str(e)}")
                return False
            except CPKProjectPushException:
                cpklogger.error(f"An error occurred while building the project image.")
                return False

        cpklogger.info("Image pushed successfully!")
