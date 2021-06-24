import argparse
import copy
import datetime
import json
import sys
import time
from typing import Optional

from docker.errors import ImageNotFound, APIError
from termcolor import colored

from cpk import CPKProject, cpkconfig
from cpk.utils.docker import transfer_image
from cpk.utils.misc import human_time, configure_binfmt
from .endpoint import CLIEndpointInfoCommand
from .info import CLIInfoCommand
from .. import AbstractCLICommand
from ..logger import cpklogger
from ...constants import ARCH_TO_DOCKER_PLATFORM
from ...exceptions import CPKProjectBuildException
from ...types import Machine, Arguments
from ...utils.cli import check_git_status
from ...utils.image_analyzer import EXTRA_INFO_SEPARATOR, ImageAnalyzer, SEPARATORS_LENGTH
from ...utils.machine import get_machine


class CLIBuildCommand(AbstractCLICommand):

    KEY = 'build'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        parser.add_argument(
            "--pull",
            default=False,
            action="store_true",
            help="Whether to pull the latest base image used by the Dockerfile",
        )
        parser.add_argument(
            "--no-cache",
            default=False,
            action="store_true",
            help="Whether to use the Docker cache"
        )
        parser.add_argument(
            "--force-cache",
            default=False,
            action="store_true",
            help="Whether to force Docker to use an old version of the same image as cache",
        )
        parser.add_argument(
            "--no-multiarch",
            default=False,
            action="store_true",
            help="Whether to disable multiarch support (based on bin_fmt)",
        )
        parser.add_argument(
            "-A",
            "--build-arg",
            default=[],
            action="append",
            nargs=2,
            metavar=('key', 'value'),
            help="Build arguments to pass to Docker build",
        )
        parser.add_argument(
            "--push",
            default=False,
            action="store_true",
            help="Whether to push the resulting image"
        )
        parser.add_argument(
            "--rm",
            default=False,
            action="store_true",
            help="Remove the images once the build is finished (after pushing)",
        )
        parser.add_argument(
            "-b",
            "--base-tag",
            default=None,
            help="Docker tag for the base image. "
                 "Use when the base image is also a development version",
        )
        parser.add_argument(
            "--stamp",
            default=False,
            action="store_true",
            help="Stamp image with the build time"
        )
        # TODO: to be implemented
        parser.add_argument(
            "-D",
            "--destination",
            default=None,
            help="CPK machine or endpoint hostname where to deliver the image once built"
        )
        # TODO: to be implemented
        parser.add_argument(
            "--docs",
            default=False,
            action="store_true",
            help="Build the code documentation as well"
        )
        parser.add_argument(
            "--tag",
            default=None,
            type=str,
            help="Custom tag"
        )
        parser.add_argument(
            "--ncpus",
            default=None,
            type=int,
            help="Value to pass as build-arg `NCPUS` to docker build."
        )
        return parser

    @staticmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        stime = time.time()

        # get project
        project = CPKProject(parsed.workdir, parsed=parsed)

        # show info about project
        CLIInfoCommand.execute(None, parsed)

        # check git workspace status
        proceed = check_git_status(project, parsed)
        if not proceed:
            return False

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

        # define build-args
        buildargs = {"buildargs": {}, "labels": {}}
        # - add project build args
        buildargs["buildargs"].update({
            "ARCH": parsed.arch,
            "NAME": project.name,
            "DESCRIPTION": project.description,
            "ORGANIZATION": project.organization,
            "MAINTAINER": project.maintainer
        })
        # - add project labels
        buildargs["labels"].update(project.build_labels())
        # - build-arg NCPUS
        buildargs['buildargs']['NCPUS'] = \
            str(parsed.ncpus) if parsed.ncpus else str(machine.get_ncpus())

        # create defaults
        image = project.image(parsed.arch)

        # print info about multiarch
        cpklogger.info("Building an image for {} on {}.".format(parsed.arch, machine_arch))
        # - register bin_fmt in the target machine (if needed)
        if not parsed.no_multiarch:
            configure_binfmt(machine_arch, parsed.arch, docker, cpklogger)
        platform = ARCH_TO_DOCKER_PLATFORM.get(parsed.arch, None)

        # architecture target
        buildargs["buildargs"]["ARCH"] = parsed.arch

        # development base images
        if parsed.base_tag is not None:
            buildargs["buildargs"]["DISTRO"] = parsed.base_tag

        # custom build arguments
        for key, value in parsed.build_arg:
            buildargs["buildargs"][key] = value

        # cache
        if not parsed.no_cache:
            # check if the endpoint contains an image with the same name
            try:
                docker.images.get(image)
                is_present = True
            except (ImageNotFound, BaseException):
                is_present = False
            # ---
            if not is_present and parsed.pull:
                # try to pull the same image so Docker can use it as cache source
                cpklogger.info(f'Pulling image "{image}" to use as cache...')
                try:
                    machine.pull_image(image)
                    is_present = True
                except KeyboardInterrupt:
                    cpklogger.info("Aborting.")
                    return False
                except (ImageNotFound, BaseException):
                    cpklogger.warning(
                        f'An error occurred while pulling the image "{image}", maybe the '
                        "image does not exist"
                    )
            else:
                cpklogger.info("Found an image with the same name. Using it as cache source.")
            # configure cache
            if parsed.force_cache and is_present:
                buildargs["cache_from"] = [image]

        # stamp image
        build_time = "ND"
        if parsed.stamp:
            if project.is_dirty():
                cpklogger.error(
                    "Your git index is not clean. You can't stamp an image built "
                    "from a dirty index."
                )
                return False
            else:
                # project is clean
                build_time = None
                local_sha = project.version.sha
                # get remote image metadata
                try:
                    # TODO: parsed.machine is now NONE
                    labels = project.image_labels(parsed.machine, parsed.arch)
                    time_label = project.label("time")
                    sha_label = project.label("code.sha")
                    if time_label in labels and sha_label in labels:
                        remote_time = labels[time_label]
                        remote_sha = labels[sha_label]
                        if remote_sha == local_sha and remote_time != "ND":
                            cpklogger.debug("Identical image found. Reusing cache.")
                            # local and remote SHA match, reuse time
                            build_time = remote_time
                except BaseException as e:
                    cpklogger.warning(f"Cannot fetch image metadata. Reason: {str(e)}")
        # default build_time
        build_time = build_time or datetime.datetime.utcnow().isoformat()
        cpklogger.debug(f"Image timestamp: {build_time}")
        # add timestamp label
        buildargs["labels"][project.label("time")] = build_time

        # collect build args
        buildargs.update(
            {
                "path": project.path,
                "rm": True,
                "pull": parsed.pull,
                "nocache": parsed.no_cache,
                "tag": image,
                "platform": platform
            }
        )
        cpklogger.debug("Build arguments:\n%s\n" % json.dumps(buildargs, sort_keys=True, indent=4))

        # build image
        buildlog = []
        print("=" * SEPARATORS_LENGTH)
        try:
            for line in docker.api.build(**buildargs, decode=True):
                line = _build_line(line)
                if not line:
                    continue
                try:
                    sys.stdout.write(line)
                    buildlog.append(line)
                except UnicodeEncodeError:
                    pass
        except APIError as e:
            cpklogger.error(f"An error occurred while building the project image:\n{str(e)}")
            return False
        except CPKProjectBuildException:
            cpklogger.error(f"An error occurred while building the project image.")
            return False
        dimage = docker.images.get(image)

        # tag release images
        if project.is_release():
            rimage = project.image_release(parsed.arch)
            dimage.tag(*rimage.split(":"))
            msg = f"Successfully tagged {rimage}"
            buildlog.append(msg)
            cpklogger.print(msg)

        # TODO: fix this
        # # build code docs
        # if parsed.docs:
        #     docs_args = ["--quiet"] * int(not parsed.verbose)
        #     # build docs
        #     cpklogger.info("Building documentation...")

        # get image history
        historylog = [(layer["Id"], layer["Size"]) for layer in dimage.history()]

        # round up extra info
        extra_info = []
        # - launchers info
        launchers = project.launchers()
        if len(launchers) > 0:
            extra_info.append("Image launchers:")
            for launcher in sorted(launchers):
                extra_info.append(" - {:s}".format(launcher))
            extra_info.append(EXTRA_INFO_SEPARATOR)
        # - timing
        extra_info.append("Time: {}".format(human_time(time.time() - stime)))
        # - documentation
        extra_info.append(
            "Documentation: {}".format(
                colored("Built", "green") if parsed.docs else colored("Skipped", "yellow")
            )
        )
        # compile extra info
        extra_info = "\n".join(extra_info)
        # run docker image analysis
        print("=" * SEPARATORS_LENGTH + "\n")
        cpklogger.info("Analyzing the image...")
        print()
        _, _, final_image_size = ImageAnalyzer.process(
            buildlog, historylog, extra_info=extra_info
        )
        # pull image (if the destination is different from the builder machine)
        if parsed.destination and machine.base_url != parsed.destination:
            transfer_image(
                origin=machine,
                destination=get_machine(parsed.destination, cpkconfig.machines),
                image=image,
                image_size=final_image_size,
            )
        # perform push (if needed)
        if parsed.push:
            # call command `push`
            from .push import CLIPushCommand
            CLIPushCommand.execute(machine, copy.deepcopy(parsed))

        # perform remove (if needed)
        if parsed.rm:
            from .clean import CLICleanCommand
            # noinspection PyBroadException
            try:
                # call command `clean`
                CLICleanCommand.execute(machine, copy.deepcopy(parsed))
            except BaseException:
                cpklogger.warn("We had some issues cleaning up the image. Just a heads up!")


def _build_line(line):
    if "error" in line and "errorDetail" in line:
        msg = line["errorDetail"]["message"]
        cpklogger.error(msg)
        raise CPKProjectBuildException(msg)
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
