import argparse
import copy
import json
import os
import sys
import time
import datetime
from shutil import which
from typing import Union

from termcolor import colored
from docker.errors import ImageNotFound, APIError

from .info import CLIInfoCommand
from .. import AbstractCLICommand
from ..logger import cpklogger
from cpk import CPKProject
from cpk.utils.docker import get_client, get_endpoint_ncpus, DOCKER_INFO, \
    get_endpoint_architecture, pull_image
from cpk.utils.misc import sanitize_hostname, human_size, human_time, configure_binfmt
from ...exceptions import CPKProjectBuildException
from ...utils.image_analyzer import EXTRA_INFO_SEPARATOR, ImageAnalyzer, SEPARATORS_LENGTH


class CLIBuildCommand(AbstractCLICommand):

    KEY = 'build'

    @staticmethod
    def parser(parent: Union[None, argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
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
        parser.add_argument(
            "-D",
            "--destination",
            default=None,
            help="Docker socket or hostname where to deliver the image"
        )
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
    def execute(parsed: argparse.Namespace) -> bool:
        stime = time.time()
        parsed.workdir = os.path.abspath(parsed.workdir)

        # get project
        project = CPKProject(parsed.workdir, parsed=parsed)

        # show info about project
        CLIInfoCommand.execute(parsed)

        # check if the git HEAD is detached
        if project.is_detached():
            cpklogger.error(
                "The repository HEAD is detached. Create a branch or check one out "
                "before continuing. Aborting."
            )
            return False

        # check if the index is clean
        if project.is_dirty():
            cpklogger.warning("Your index is not clean (some files are not committed).")
            cpklogger.warning("If you know what you are doing, use --force (-f) to force.")
            if not parsed.force:
                return False
            cpklogger.warning("Forced!")

        # sanitize hostname
        if parsed.machine is not None:
            parsed.machine = sanitize_hostname(parsed.machine)

        # create docker client
        docker = get_client(parsed.machine)

        # get info about docker endpoint
        cpklogger.info("Retrieving info about Docker endpoint...")
        epoint = docker.info()
        if "ServerErrors" in epoint:
            cpklogger.error("\n".join(epoint["ServerErrors"]))
            return False
        epoint["MemTotal"] = human_size(epoint["MemTotal"])
        cpklogger.print(DOCKER_INFO.format(**epoint))

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
            str(get_endpoint_ncpus(docker)) if parsed.ncpus is None else str(parsed.ncpus)

        # pick the right architecture if not set
        if parsed.arch is None:
            parsed.arch = get_endpoint_architecture(parsed.machine)
            cpklogger.info(f"Target architecture automatically set to {parsed.arch}.")

        # create defaults
        image = project.image(parsed.arch)

        # print info about multiarch
        msg = "Building an image for {} on {}.".format(parsed.arch, epoint["Architecture"])
        cpklogger.info(msg)
        # - register bin_fmt in the target machine (if needed)
        if not parsed.no_multiarch:
            configure_binfmt(parsed.arch, docker, cpklogger)

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
                    pull_image(image, endpoint=docker)
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

        # build code docs
        if parsed.docs:
            docs_args = ["--quiet"] * int(not parsed.verbose)
            # build docs
            cpklogger.info("Building documentation...")
            # TODO: fix this

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
        if parsed.destination and parsed.machine != parsed.destination:
            _transfer_image(
                origin=parsed.machine,
                destination=parsed.destination,
                image=image,
                image_size=final_image_size,
            )
        # perform push (if needed)
        if parsed.push:
            # call command `push`
            from .push import CLIPushCommand
            CLIPushCommand.execute(copy.deepcopy(parsed))

        # perform remove (if needed)
        if parsed.rm:
            from .clean import CLICleanCommand
            # noinspection PyBroadException
            try:
                # call command `clean`
                CLICleanCommand.execute(copy.deepcopy(parsed))
            except BaseException:
                cpklogger.warn(
                    "We had some issues cleaning up the image on '{:s}'".format(parsed.machine)
                    + ". Just a heads up!"
                )


def _transfer_image(origin, destination, image, image_size):
    monitor_info = "" if which("pv") else " (install `pv` to see the progress)"
    cpklogger.info(f'Transferring image "{image}": [{origin}] -> [{destination}]{monitor_info}...')
    data_source = ["docker", "-H=%s" % origin, "save", image]
    data_destination = ["docker", "-H=%s" % destination, "load"]
    progress_monitor = ["|", "pv", "-cN", "image", "-s", image_size] if which("pv") else []
    cmd = data_source + progress_monitor + data_destination
    # TODO: re-enable this
    # start_command_in_subprocess(cmd, nostdout=True)


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


