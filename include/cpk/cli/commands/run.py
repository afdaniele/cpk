import argparse
import copy
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict

import cpk.cli
from cpk.machine import SSHMachine
from docker.errors import ImageNotFound

from xdocker import get_configuration

from cpk import CPKProject
from cpk.utils.misc import configure_binfmt
from .endpoint import CLIEndpointInfoCommand
from .info import CLIInfoCommand
from .. import AbstractCLICommand
from ..logger import cpklogger
from ...exceptions import NotACPKProjectException
from ...types import CPKFileMappingTrigger, CPKMachine, Arguments, CPKFileMapping
from ...utils.cli import check_git_status

SUPPORTED_SUBCOMMANDS = [
    "attach"
]
RSYNC_DESTINATION_PATH = "/tmp/"


class CLIRunCommand(AbstractCLICommand):

    KEY = 'run'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
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
        # parser.add_argument(
        #     "--plain",
        #     default=False,
        #     action="store_true",
        #     help="Whether to run the image without default module configuration",
        # )
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
            help="Add X-Forwarding configuration (adds support for GUI applications)",
        )
        parser.add_argument(
            "-s",
            "--sync",
            default=False,
            action="store_true",
            help="Sync code from local project to remote"
        )
        parser.add_argument(
            "-sm",
            "--sync-mirror",
            default=False,
            action="store_true",
            help="Mirror code from local project to remote"
        )
        parser.add_argument(
            "--net", "--network_mode",
            dest="network_mode",
            default=None,
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
        # parser.add_argument(
        #     "subcommand",
        #     nargs="?",
        #     default=None,
        #     choices=SUPPORTED_SUBCOMMANDS,
        #     help="(Optional) Subcommand to execute"
        # )
        return parser

    @staticmethod
    def execute(machine: CPKMachine, parsed: argparse.Namespace) -> bool:
        # get project
        project = CPKProject(parsed.workdir, parsed=parsed)

        # show info about project
        CLIInfoCommand.execute(machine, parsed)

        # check git workspace status
        mount_source = parsed.mount is True or isinstance(parsed.mount, str)
        proceed = check_git_status(project, parsed, must_be_clean=mount_source)
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

        # create defaults
        image = project.image(parsed.arch)
        parsed.name = parsed.name or f"cpk-run-{project.name.replace('/', '-')}"

        # subcommand "attach"
        # TODO: this will not work with CPKMachine created from env, the host will be None
        # if parsed.subcommand == "attach":
        #     cpklogger.info(f"Attempting to attach to container '{parsed.name}'...")
        #     # run
        #     _run_cmd(
        #         [
        #             "docker",
        #             "-H=%s" % machine.host,
        #             "exec",
        #             "-it",
        #             parsed.name,
        #             "/entrypoint.sh",
        #             "bash",
        #         ],
        #         suppress_errors=True,
        #     )
        #     return True

        # environment
        environment = []
        # volumes
        volumes = []
        # module configuration
        module_configuration_args = []
        # active triggers
        triggers = {CPKFileMappingTrigger.DEFAULT.value}

        # trigger run:mount
        if mount_source:
            triggers.update({CPKFileMappingTrigger.RUN_MOUNT.value})

        # trigger launcher:<X>
        if parsed.launcher:
            triggers.update({f"launcher:{parsed.launcher}"})
        cpklogger.debug(f"Active triggers: {triggers}")

        # print info about multiarch
        cpklogger.info("Running an image for {} on {}.".format(parsed.arch, machine_arch))
        # - register bin_fmt in the target machine (if needed)
        if not parsed.no_multiarch:
            configure_binfmt(machine_arch, parsed.arch, docker, cpklogger)

        # x-docker configuration
        if parsed.use_x_docker:
            xconfig = get_configuration(docker)
            # TODO: once we switch to the DOcker SDK for Python, we should use this directly
            if "environment" in xconfig:
                for ekey, evalue in xconfig["environment"].items():
                    environment += ["-e", f"{ekey}={evalue}"]
            if "volumes" in xconfig:
                for vsrc, vdsc in xconfig["volumes"].items():
                    volumes += ["-v", "{:s}:{:s}:{:s}".format(vsrc, vdsc["bind"], vdsc["mode"])]
            if "runtime" in xconfig:
                module_configuration_args.append(f"--runtime={xconfig['runtime']}")

        # check runtime
        if shutil.which(parsed.runtime) is None:
            raise ValueError('Docker runtime binary "{}" not found!'.format(parsed.runtime))

        # network mode
        if parsed.network_mode is not None:
            module_configuration_args.append(f"--net={parsed.network_mode}")

        # mount source code (if requested)
        if mount_source:
            projects_to_mount = []
            # (always) mount current project
            paths_to_mount = [parsed.workdir] if parsed.mount is True else []
            # mount secondary projects
            if isinstance(parsed.mount, str):
                paths_to_mount.extend(
                    [os.path.join(os.getcwd(), p.strip()) for p in parsed.mount.split(",")]
                )
            # create mount points definitions
            for project_path in paths_to_mount:
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
                projects_to_mount.append(proj)
        else:
            projects_to_mount = [project]

        # sync
        sync_remote = parsed.sync or parsed.sync_mirror
        if sync_remote:
            # does not make sense to rsync without mounting
            if not mount_source:
                cpklogger.error("The options -s/--sync, -sm/--sync-mirror can only be used "
                                "together with -M/--mount")
                return False
            # only allowed when mounting remotely
            if machine.is_local:
                cpklogger.error("The options -s/--sync, -sm/--sync-mirror can only be used "
                                "together with -H/--machine")
                return False
            # only allowed with SSH machines
            if not isinstance(machine, SSHMachine):
                cpklogger.error("The options -s/--sync, -sm/--sync-mirror can only be used "
                                "with SSH-based machines")
                return False
            # make sure rsync is installed
            if shutil.which("rsync") is None:
                cpklogger.error("The options -s/--sync, -sm/--sync-mirror requires the 'rsync' "
                                "tool. Please, install it and retry.")
                return False

        # mountpoints
        mountpoints: Dict[str, str] = {}
        rsync_mountpoints: Dict[str, str] = {}

        def _mount(_proj: CPKProject, _mapping: CPKFileMapping):
            # mountapoint source on the local machine (never depends on rsync)
            local_source_path = _proj.path
            local_mountpoint_source = _mapping.source if os.path.isabs(_mapping.source) else \
                os.path.join(local_source_path, _mapping.source)
            # mountpoint source to pass to docker (depends on rsync)
            source_path = _proj.path if not sync_remote else \
                os.path.join(RSYNC_DESTINATION_PATH, os.path.abspath(_proj.path).lstrip("/"))
            mountpoint_source = _mapping.source if os.path.isabs(_mapping.source) else \
                os.path.join(source_path, _mapping.source)
            # mountpoint destination (never depends on rsync)
            mountpoint_destination = _mapping.destination
            # mountpoint mode (i.e., ro, rw, etc)
            mode = _mapping.mode
            # resolve paths
            local_mountpoint_source = str(Path(local_mountpoint_source).resolve())
            mountpoint_source = str(Path(mountpoint_source).resolve())
            mountpoint_destination = str(Path(mountpoint_destination).resolve())
            # make sure we have no conflicts of mountpoints
            conflict = mountpoints.get(mountpoint_destination, None)
            if conflict not in [None, local_mountpoint_source]:
                cpklogger.error(f"Mountpoint '{mountpoint_destination}' inside the container "
                                f"wants to be claimed by both '{conflict}' and "
                                f"'{local_mountpoint_source}'.")
                return False
            # compile mounpoints and add them to list
            volumes.extend([
                "-v", "{:s}:{:s}:{:s}".format(mountpoint_source, mountpoint_destination, mode)
            ])
            mountpoints[mountpoint_destination] = local_mountpoint_source
            # only non-absolute paths can be rsynced
            if not os.path.isabs(_mapping.source):
                rsync_mountpoints[mountpoint_source] = local_mountpoint_source
            # ---
            return True

        # mappings
        for proj in projects_to_mount:
            # iterate over list of mappings
            for mapping in proj.mappings:
                if len(triggers.intersection(mapping.triggers)) <= 0:
                    continue
                # ---
                success = _mount(proj, mapping)
                if not success:
                    return False

        # sync
        if sync_remote:
            cpklogger.info(f"Syncing mountpoints...")
            remote_base = f"{machine.user}@{machine.host}"
            for rsync_destination, rsync_source in rsync_mountpoints.items():
                # rsync options
                rsync_options = "" if not parsed.sync_mirror else "--delete"
                rsync_options += f" --rsync-path=\"mkdir -p {rsync_destination} && rsync\""
                # run rsync
                remote_path = f"{remote_base}:{rsync_destination}".rstrip('/') + '/'
                cpklogger.info(f"Syncing mountpoint [{rsync_source}] -> [{remote_path}]")
                cmd = f"rsync --archive {rsync_options} {rsync_source}/ {remote_path}"
                _run_cmd(cmd, shell=True)
            cpklogger.info(f"Mountpoints synced!")

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
                machine.pull_image(image)

        # cmd option
        if parsed.cmd and parsed.launcher:
            raise ValueError("You cannot use the option --launcher together with --cmd.")

        # launcher
        if parsed.launcher:
            environment.extend(["-e", f"CPK_LAUNCHER={parsed.launcher}"])

        cmd_option = [] if not parsed.cmd else [parsed.cmd]
        cmd_arguments = ["--"] + cpk.cli.arguments.positional2 \
            if cpk.cli.arguments.positional2 else []

        # endpoint arguments
        docker_epoint_args = []
        # TODO: this should be using the Python SDK for Docker, not Docker CLI
        if machine.base_url is not None:
            docker_epoint_args += ["-H", machine.base_url]

        # docker arguments
        docker_args = copy.copy(cpk.cli.arguments.positional1)
        if not parsed.keep:
            docker_args += ["--rm"]
        if parsed.detach:
            docker_args += ["-d"]

        # add container name to docker args
        docker_args += ["--name", parsed.name]
        # escape spaces in arguments
        docker_args = [a.replace(" ", "\\ ") for a in docker_args]

        # run
        exitcode = _run_cmd(
            [parsed.runtime]
            + docker_epoint_args
            + ["run", "-it"]
            + module_configuration_args
            + environment
            + docker_args
            + volumes
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


def _run_cmd(cmd, get_output=False, print_output=False, suppress_errors=False, shell=False,
             return_exitcode=False):
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
