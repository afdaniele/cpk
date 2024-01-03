import argparse
import copy
import datetime
import json
import sys
import time
from typing import Optional, Iterator, List

import cpk
from dockertown.components.image.models import ImageHistoryLayer
from dockertown.exceptions import NoSuchImage, DockerException
from termcolor import colored

from .endpoint import CLIEndpointInfoCommand
from .info import CLIInfoCommand
from .. import AbstractCLICommand
from ..logger import cpklogger
from ..utils import combine_args
from ...project import CPKProject
from ...constants import ARCH_TO_DOCKER_PLATFORM
from ...exceptions import CPKProjectBuildException
from ...types import Arguments, CPKMachine
from ...utils.cli import check_git_status
from ...utils.misc import human_time, configure_binfmt
from ...utils.image_analyzer import EXTRA_INFO_SEPARATOR, ImageAnalyzer, SEPARATORS_LENGTH


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
    def execute(machine: CPKMachine, parsed: argparse.Namespace, **kwargs) -> bool:
        # combine arguments
        parsed = combine_args(parsed, kwargs)
        # ---
        stime = time.time()

        # get project
        project = CPKProject(parsed.workdir)

        # show info about project
        CLIInfoCommand.execute(None, parsed)

        # check git workspace status
        proceed = check_git_status(project, parsed)
        if not proceed:
            return False

        # get info about docker endpoint
        CLIEndpointInfoCommand.execute(machine, parsed, quiet=True)

        # pick right value of `arch` given endpoint
        machine_arch = machine.get_architecture()
        if parsed.arch is None:
            cpklogger.info("Parameter `arch` not given, will resolve it from the endpoint.")
            parsed.arch = machine_arch
            cpklogger.info(f"Parameter `arch` automatically set to `{parsed.arch}`.")

        # create docker client
        docker = machine.get_client()

        # define build-args
        buildargs = {"build_args": {}, "labels": {}}
        # - add project build args
        buildargs["build_args"].update({
            "ARCH": parsed.arch,
            "PROJECT_NAME": project.name,
            "BASE_REGISTRY": project.layers.base.registry,
            "BASE_ORGANIZATION": project.layers.base.organization,
            "BASE_REPOSITORY": project.layers.base.repository,
            "BASE_TAG": project.layers.base.tag if parsed.base_tag is None else parsed.base_tag,
        })
        # - add project labels
        buildargs["labels"].update(project.build_labels())
        # - build-arg NCPUS
        buildargs['build_args']['NCPUS'] = str(parsed.ncpus) if parsed.ncpus else str(machine.get_ncpus())

        # create defaults
        image: str = project.docker.image.name(arch=parsed.arch).compile()

        # print info about multiarch
        cpklogger.info("Building an image for {} on {}.".format(parsed.arch, machine_arch))
        # - register bin_fmt in the target machine (if needed)
        if not parsed.no_multiarch:
            configure_binfmt(machine_arch, parsed.arch, docker, cpklogger)
        platform = ARCH_TO_DOCKER_PLATFORM.get(parsed.arch, None)

        # custom build arguments
        for key, value in parsed.build_arg:
            buildargs["build_args"][key] = value

        # cache
        if not parsed.no_cache:
            # check if the endpoint contains an image with the same name
            try:
                docker.image.inspect(image)
                is_present = True
            except (NoSuchImage, BaseException):
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
                except (NoSuchImage, BaseException):
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
                # TODO: this can be None
                local_sha = project.repository.sha
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
                "pull": parsed.pull,
                "cache": not parsed.no_cache,
                "tags": image,
                "platforms": [platform]
            }
        )
        cpklogger.debug("Build arguments:\n%s\n" % json.dumps(buildargs, sort_keys=True, indent=4))

        # build image
        build_log = []
        print("=" * SEPARATORS_LENGTH)
        try:
            lines: Iterator[str] = docker.buildx.build(
                **buildargs,
                progress="plain",
                stream_logs=True
            )

            for line in lines:
                if not line:
                    continue
                try:
                    sys.stdout.write(line)
                    build_log.append(line)
                except UnicodeEncodeError:
                    pass
        except DockerException as e:
            cpklogger.error(f"An error occurred while building the project image:\n{str(e)}")
            return False
        except CPKProjectBuildException:
            cpklogger.error(f"An error occurred while building the project image.")
            return False
        dimage = docker.image.inspect(image)

        # tag release images
        if project.is_release():
            rimage: str = project.docker.image.release_name(parsed.arch).compile()
            dimage.tag(*rimage.split(":"))
            msg = f"Successfully tagged {rimage}"
            build_log.append(msg)
            print(msg)

        # get image history
        image_history: List[ImageHistoryLayer] = docker.image.history(image)

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
        # compile extra info
        extra_info = "\n".join(extra_info)

        # run docker image analysis
        print("=" * SEPARATORS_LENGTH + "\n")
        cpklogger.info("Analyzing the image...")
        ImageAnalyzer.process(image_history, build_log, extra_info=extra_info)
        footer: str = f"cpk - v{cpk.__version__}"
        # print footer
        print(" " * (SEPARATORS_LENGTH - len(footer)) + footer)

        # perform push (if needed)
        if parsed.push:
            # call command `push`
            from .push import CLIPushCommand
            push_args = copy.deepcopy(parsed)
            push_args.release = False
            CLIPushCommand.execute(machine, push_args)

        # perform remove (if needed)
        if parsed.rm:
            from .clean import CLICleanCommand
            # noinspection PyBroadException
            try:
                # call command `clean`
                CLICleanCommand.execute(machine, copy.deepcopy(parsed))
            except BaseException:
                cpklogger.warn("We had some issues cleaning up the image. Just a heads up!")
