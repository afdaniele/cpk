import argparse
import time
from typing import Optional

from docker.errors import APIError

from .endpoint import CLIEndpointInfoCommand
from .info import CLIInfoCommand
from .. import AbstractCLICommand, cpklogger
from ... import CPKProject
from ...exceptions import CPKProjectPushException
from ...types import Machine, Arguments
from ...utils.cli import check_git_status


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
        return parser

    @staticmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        stime = time.time()

        # get project
        project = CPKProject(parsed.workdir, parsed=parsed)

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

        # create docker client
        docker = machine.get_client()

        # create defaults
        image = project.image(parsed.arch)

        # print info about multiarch
        msg = "Pushing image {} to {}.".format(image, project.registry)
        cpklogger.info(msg)

        # push image
        try:
            for line in docker.api.push(image, decode=True):
                line = _push_line(line)
                print(line)
                # if not line:
                #     continue
                # try:
                #     sys.stdout.write(line)
                # except UnicodeEncodeError:
                #     pass
        except APIError as e:
            cpklogger.error(f"An error occurred while pushing the project image:\n{str(e)}")
            return False
        except CPKProjectPushException:
            cpklogger.error(f"An error occurred while building the project image.")
            return False

        cpklogger.info("Image pushed successfully!")


def _push_line(line):
    if "error" in line and "errorDetail" in line:
        msg = line["errorDetail"]["message"]
        cpklogger.error(msg)
        raise CPKProjectPushException(msg)
    if "stream" not in line:
        return None
    line = line["stream"].strip("\n")
    if not line:
        return None
    # this allows apps inside docker build to clear lines
    if not line.endswith("\r"):
        line += "\n"
    # ---
    return line
