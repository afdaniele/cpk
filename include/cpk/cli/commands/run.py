import argparse
import os
import shutil
import subprocess
from typing import Union

from docker.errors import ImageNotFound

from cpk import CPKProject
from cpk.utils.docker import get_client, DOCKER_INFO, \
    get_endpoint_architecture, pull_image
from cpk.utils.misc import sanitize_hostname, human_size, configure_binfmt
from .info import CLIInfoCommand
from .. import AbstractCLICommand
from ..logger import cpklogger
from ...exceptions import NotACPKProjectException
from ...types import CPKFileMappingTrigger

DEFAULT_NETWORK_MODE = "bridge"
SUPPORTED_SUBCOMMANDS = [
    "attach"
]
TRIGGERS = {CPKFileMappingTrigger.DEFAULT, CPKFileMappingTrigger.RUN_MOUNT}


class CLIRunCommand(AbstractCLICommand):

    KEY = 'run'

    @staticmethod
    def parser(parent: Union[None, argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        parser.add_argument(
            "-n",
            "--name",
            default=None,
            help="Name of the container"
        )
        parser.add_argument(
            "-c",
            "--cmd",
            default=None,
            help="Command to run in the Docker container"
        )
        parser.add_argument(
            "--pull",
            default=False,
            action="store_true",
            help="Whether to pull the latest image available",
        )
        parser.add_argument(
            "--force-pull",
            default=False,
            action="store_true",
            help="Whether to force pull the image of the project",
        )
        parser.add_argument(
            "--plain",
            default=False,
            action="store_true",
            help="Whether to run the image without default module configuration",
        )
        parser.add_argument(
            "--no-multiarch",
            default=False,
            action="store_true",
            help="Whether to disable multiarch support (based on bin_fmt)",
        )
        parser.add_argument(
            "-M",
            "--mount",
            default=False,
            const=True,
            action="store",
            nargs="?",
            type=str,
            help="Whether to mount the current project into the container. "
                 "Pass a comma-separated list of paths to mount multiple projects",
        )
        parser.add_argument(
            "--keep",
            default=False,
            action="store_true",
            help="Whether to NOT remove the container once stopped"
        )
        parser.add_argument(
            "-L",
            "--launcher",
            default=None,
            help="Launcher to invoke inside the container",
        )
        parser.add_argument(
            "-A",
            "--argument",
            dest="arguments",
            default=[],
            action="append",
            help="Arguments for the container command",
        )
        parser.add_argument(
            "--runtime",
            default="docker",
            type=str,
            help="Docker runtime to use to run the container"
        )
        parser.add_argument(
            "-X",
            dest="use_x_docker",
            default=False,
            action="store_true",
            help="Use x-docker as runtime",
        )
        parser.add_argument(
            "-s",
            "--sync",
            default=False,
            action="store_true",
            help="Sync code from local project to remote"
        )
        parser.add_argument(
            "--net", "--network_mode",
            dest="network_mode",
            default=DEFAULT_NETWORK_MODE,
            type=str,
            help="Docker network mode"
        )
        parser.add_argument(
            "-d",
            "--detach",
            default=False,
            action="store_true",
            help="Detach from the container and let it run"
        )
        parser.add_argument(
            "--tag",
            default=None,
            type=str,
            help="Custom tag"
        )
        parser.add_argument(
            "docker_args",
            nargs="*",
            default=[]
        )
        parser.add_argument(
            "subcommand",
            nargs="?",
            default=None,
            choices=SUPPORTED_SUBCOMMANDS,
            help="(Optional) Subcommand to execute"
        )
        return parser

    @staticmethod
    def execute(parsed: argparse.Namespace) -> bool:
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
        mount_source = parsed.mount is True or isinstance(parsed.mount, str)
        if project.is_dirty() and mount_source:
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

        # pick the right architecture if not set
        if parsed.arch is None:
            parsed.arch = get_endpoint_architecture(parsed.machine)
            cpklogger.info(f"Target architecture automatically set to {parsed.arch}.")

        # create defaults
        image = project.image(parsed.arch)
        parsed.name = parsed.name or f"cpk-run-{project.name}"

        # subcommand "attach"
        if parsed.subcommand == "attach":
            cpklogger.info(f"Attempting to attach to container '{parsed.name}'...")
            # run
            _run_cmd(
                [
                    "docker",
                    "-H=%s" % parsed.machine,
                    "exec",
                    "-it",
                    parsed.name,
                    "/entrypoint.sh",
                    "bash",
                ],
                suppress_errors=True,
            )
            return True

        # print info about multiarch
        msg = "Running an image for {} on {}.".format(parsed.arch, epoint["Architecture"])
        cpklogger.info(msg)
        # - register bin_fmt in the target machine (if needed)
        if not parsed.no_multiarch:
            configure_binfmt(parsed.arch, docker, cpklogger)

        # ---
        # TODO: this is wrong, x-docker should either be a Python package that gives us the
        #  configuration for X-Forwarding on THIS computer, or a proper docker-runtime that
        #  we can pass to the Python SDK for Docker
        # x-docker runtime
        if parsed.use_x_docker:
            command_dir = os.path.dirname(os.path.abspath(__file__))
            parsed.runtime = os.path.join(command_dir, "x-docker")
        # check runtime
        if shutil.which(parsed.runtime) is None:
            raise ValueError('Docker runtime binary "{}" not found!'.format(parsed.runtime))
        # ---

        # pick the right architecture if not set
        if parsed.arch is None:
            parsed.arch = get_endpoint_architecture(parsed.machine)
            cpklogger.info(f"Target architecture automatically set to {parsed.arch}.")

        # create the module configuration
        module_configuration_args = [
            f"--net={parsed.network_mode}"
        ]

        # mount code
        mount_option = []
        # mount source code (if requested)
        if mount_source:
            # (always) mount current project
            projects_to_mount = [parsed.workdir] if parsed.mount is True else []
            # mount secondary projects
            if isinstance(parsed.mount, str):
                projects_to_mount.extend(
                    [os.path.join(os.getcwd(), p.strip()) for p in parsed.mount.split(",")]
                )
            # create mount points definitions
            for project_path in projects_to_mount:
                # make sure that the project exists
                if not os.path.isdir(project_path):
                    cpklogger.error('The path "{:s}" is not a CPK project'.format(project_path))
                    return False
                # get project info
                try:
                    proj = CPKProject(project_path)
                except NotACPKProjectException:
                    cpklogger.error(f"The path '{project_path}' does not contain a CPK project.")
                    return False
                # iterate over list of mappings
                for mapping in proj.mappings:
                    if TRIGGERS.intersection(set(mapping.triggers)):
                        mpoint_source = mapping.source if os.path.isabs(mapping.source) else \
                            os.path.join(project_path, mapping.source)
                        mpoint_destination = mapping.destination
                        # compile mounpoints
                        mount_option += [
                            "-v", "{:s}:{:s}".format(mpoint_source, mpoint_destination)
                        ]

        # pulling image (if requested)
        if parsed.pull or parsed.force_pull:
            present = False
            try:
                docker.images.get(image)
                present = True
            except ImageNotFound:
                pass
            if present and not parsed.force_pull:
                cpklogger.info("Found an image with the same name. Use --force-pull to pull again")
            else:
                cpklogger.info('Pulling image "%s"...' % image)
                pull_image(image, docker)

        # cmd option
        if parsed.cmd and parsed.launcher:
            raise ValueError("You cannot use the option --launcher together with --cmd.")

        # environment
        environment = []
        if parsed.launcher:
            environment.extend(["-e", f"CPK_LAUNCHER={parsed.launcher}"])

        cmd_option = [] if not parsed.cmd else [parsed.cmd]
        cmd_arguments = (
            [] if not parsed.arguments else ["--"] + list(
                map(lambda s: "--%s" % s, parsed.arguments))
        )

        # endpoint arguments
        docker_epoint_args = []
        if parsed.machine is not None:
            docker_epoint_args += ["-H", parsed.machine]

        # docker arguments
        if not parsed.docker_args:
            parsed.docker_args = []
        if (not parsed.keep) or (not parsed.detach):
            parsed.docker_args += ["--rm"]
        if parsed.detach:
            parsed.docker_args += ["-d"]

        # add container name to docker args
        parsed.docker_args += ["--name", parsed.name]
        # escape spaces in arguments
        parsed.docker_args = [a.replace(" ", "\\ ") for a in parsed.docker_args]
        # run
        exitcode = _run_cmd(
            [parsed.runtime]
            + docker_epoint_args
            + ["run", "-it"]
            + module_configuration_args
            + environment
            + parsed.docker_args
            + mount_option
            + [image]
            + cmd_option
            + cmd_arguments,
            suppress_errors=True,
            return_exitcode=True
        )
        if parsed.detach:
            cpklogger.info("Your container is running in detached mode!")
        else:
            cpklogger.debug(f"Command exited with exit code [{exitcode}].")


def _run_cmd(cmd, get_output=False, print_output=False, suppress_errors=False, shell=False, return_exitcode=False):
    if shell and isinstance(cmd, (list, tuple)):
        cmd = " ".join([str(s) for s in cmd])
    cpklogger.debug("$ %s" % cmd)
    if get_output:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=shell)
        proc.wait()
        if proc.returncode != 0:
            if not suppress_errors:
                msg = "The command {} returned exit code {}".format(cmd, proc.returncode)
                cpklogger.error(msg)
                raise RuntimeError(msg)
        out = proc.stdout.read().decode("utf-8").rstrip()
        if print_output:
            print(out)
        return out
    else:
        if return_exitcode:
            res = subprocess.run(cmd, shell=shell)
            return res.returncode
        else:
            try:
                subprocess.check_call(cmd, shell=shell)
            except subprocess.CalledProcessError as e:
                if not suppress_errors:
                    raise e
