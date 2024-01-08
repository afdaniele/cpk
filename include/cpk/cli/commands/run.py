import argparse
import os
import random
import shutil
import string
import subprocess
from typing import Optional, Set, List

import cpk.cli
import dockertown.exceptions
from cpk import CPKProject
from cpk.machine import SSHMachine
from cpk.utils.misc import configure_binfmt
from dockertown import DockerClient
from .endpoint import CLIEndpointInfoCommand
from .info import CLIInfoCommand
from .. import AbstractCLICommand
from ..logger import cpklogger
from ..utils import combine_args, pretty_json
from ...exceptions import NotACPKProjectException
from ...types import CPKMachine, Arguments, DockertownContainerConfiguration

RSYNC_DESTINATION_PATH = "/tmp/cpk/"
DEFAULT_LAUNCHER = "default"
DEFAULT_CONFIGURATION = "default"


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
            "--cmd",
            default=None,
            help="Command to run in the Docker container"
        )
        parser.add_argument(
            "--pull",
            default="missing",
            const="always",
            nargs="?",
            choices=["always", "missing", "never"],
            type=str,
            help="The pull policy to use. (default: 'pull only if missing')",
        )
        parser.add_argument(
            "--plain",
            default=False,
            action="store_true",
            help="Whether to run the image with an empty container configuration",
        )
        parser.add_argument(
            "-c", "--configuration",
            default=None,
            type=str,
            help="Container configuration to run the container with (default: 'default')",
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
            default=None,
            action="append",
            type=str,
            help="Path to other CPKProjects to mount inside the container (default: current project). "
                 "Can be used multiple times to mount multiple projects.",
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
            default=DEFAULT_LAUNCHER,
            help="Launcher to invoke inside the container",
        )
        parser.add_argument(
            "--runtime",
            default=None,
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
            "-l",
            "--no-sync",
            default=False,
            action="store_true",
            help="Do not sync local and remote projects"
        )
        parser.add_argument(
            "--net",
            "--network_mode",
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
        CLIEndpointInfoCommand.execute(machine, parsed, quiet=True)

        # pick right value of `arch` given endpoint
        machine_arch: str = machine.get_architecture()
        if parsed.arch is None:
            cpklogger.info("Parameter `arch` not given, will resolve it from the endpoint.")
            parsed.arch = machine_arch
            cpklogger.info(f"Parameter `arch` automatically set to `{parsed.arch}`.")

        # check runtime
        if parsed.runtime is not None and shutil.which(parsed.runtime) is None:
            raise ValueError('Docker runtime binary "{}" not found!'.format(parsed.runtime))

        # check other projects to mount
        projects_to_mount: List[CPKProject] = []
        for p in (parsed.mount or []):
            if not os.path.isdir(p):
                cpklogger.error('The path "{:s}" is not a CPK project'.format(p))
                return False
            try:
                proj: CPKProject = CPKProject(p)
            except NotACPKProjectException:
                cpklogger.error(f"The path '{p}' does not contain a CPK project.")
                return False
            projects_to_mount.append(proj)

        # check network mode
        if parsed.network_mode not in [None, "host", "bridge"]:
            cpklogger.error(f"Invalid network mode '{parsed.network_mode}'. "
                            f"Valid network modes are 'host' and 'bridge'.")
            return False

        # check colliding options
        if parsed.plain and parsed.mount:
            cpklogger.error("You cannot use the option --plain together with --mount.")
            return False
        if parsed.plain and parsed.configuration is not None:
            cpklogger.error("You cannot use the option --plain together with --configuration.")
            return False
        parsed.configuration = None if parsed.plain else (parsed.configuration or DEFAULT_CONFIGURATION)

        # create docker client
        docker: DockerClient = machine.get_client()

        # triggers
        triggers: Set[str] = {"run"}
        # - plain trigger
        if parsed.plain:
            triggers.add("run:plain")
        # - launcher trigger
        if parsed.launcher:
            triggers.update({f"run:launcher:{parsed.launcher}"})
        cpklogger.debug(f"Active triggers: {triggers}")

        # configure multiarch (if needed)
        cpklogger.info("Running an image for {} on {}.".format(parsed.arch, machine_arch))
        # - register bin_fmt in the target machine (if needed)
        if not parsed.no_multiarch:
            configure_binfmt(machine_arch, parsed.arch, docker, cpklogger)

        # sync
        sync_remote: bool = not machine.is_local and not parsed.no_sync
        if sync_remote:
            # only allowed with SSH machines
            if not isinstance(machine, SSHMachine):
                cpklogger.warning("You are not using an SSH machine. Project syncing will not be possible.")
                sync_remote = False
            # make sure rsync is installed
            if shutil.which("rsync") is None:
                cpklogger.warning("Project synchronization with a remote machine requires the 'rsync' "
                                  "tool to be installed. Please, install it to enable remote sync.")
                sync_remote = False

        # create container configuration
        configuration: DockertownContainerConfiguration
        if parsed.configuration is None:
            # plain
            configuration = DockertownContainerConfiguration()
        else:
            if not project.layers.containers.has(parsed.configuration):
                cpklogger.error(f"Configuration '{parsed.configuration}' not found in project. "
                                f"Valid configuration are: [{', '.join(project.layers.containers.keys)}]")
                return False
            configuration = project.configuration(parsed.configuration).as_dockertown_configuration()

        # merge projects' configurations together
        if not parsed.plain:
            for proj in projects_to_mount:
                cfg = proj.configuration(DEFAULT_CONFIGURATION).as_dockertown_configuration()
                configuration.merge(config=cfg, project=proj, exclude=["name"])

        # image name
        configuration.image = project.docker.image.name(parsed.arch).compile()

        # container name
        random_str = ''.join(random.choice(string.ascii_lowercase) for _ in range(8))
        container_name: str = f"cpk-run-{project.name.replace('/', '-')}-{random_str}"
        configuration.name = container_name

        # pull policy
        configuration.pull = parsed.pull

        # runtime
        configuration.runtime = parsed.runtime

        # detach
        configuration.detach = parsed.detach

        # remove
        configuration.remove = not parsed.keep

        # interactive
        configuration.interactive = True
        configuration.tty = True

        # launcher
        if parsed.launcher:
            configuration.envs["CPK_LAUNCHER"] = parsed.launcher

        # passthrough arguments to docker (anything passed after `--`)
        configuration.x_passthrough_args = cpk.cli.arguments.positional1

        # container command (anything passed after `++`)
        configuration.command = (["--"] + cpk.cli.arguments.positional2) \
            if cpk.cli.arguments.positional2 else []

        # network mode
        if parsed.network_mode is not None:
            configuration.networks = [parsed.network_mode]

        # sync
        if sync_remote:
            cpklogger.info(f"Syncing project...")
            remote_base = f"{machine.user}@{machine.host}"
            for host_path, container_path, *_ in configuration.volumes:
                # only sync if source is not absolute
                if os.path.isabs(host_path):
                    continue
                rsync_source: str = os.path.abspath(host_path)
                rsync_destination: str = os.path.join(
                    RSYNC_DESTINATION_PATH, project.name, host_path.lstrip("/")
                )
                # rsync options
                rsync_options = f"--archive --delete --rsync-path=\"mkdir -p {rsync_destination} && rsync\""
                # run rsync
                remote_path = f"{remote_base}:{rsync_destination}".rstrip('/') + '/'
                cpklogger.info(f"Syncing mountpoint [{rsync_source}] -> [{remote_path}]")
                cmd = f"rsync {rsync_options} {rsync_source}/ {remote_path}"
                _run_cmd(cmd, shell=True)
            cpklogger.info(f"Project synced!")

        # x-docker configuration
        if parsed.use_x_docker:
            # TODO: write an util that returns a DockertownContainerConfiguration that we can merge in
            # xconfig: dict = get_configuration(docker)
            # if "environment" in xconfig:
            #     for ekey, evalue in xconfig["environment"].items():
            #         environment += ["-e", f"{ekey}={evalue}"]
            # if "volumes" in xconfig:
            #     for vsrc, vdsc in xconfig["volumes"].items():
            #         volumes += ["-v", "{:s}:{:s}:{:s}".format(vsrc, vdsc["bind"], vdsc["mode"])]
            # if "runtime" in xconfig:
            #     module_configuration_args.append(f"--runtime={xconfig['runtime']}")
            pass

        # def _mount(_proj: CPKProject, _mapping: CPKFileMapping):
        #     # mountapoint source on the local machine (never depends on rsync)
        #     local_source_path = _proj.path
        #     local_mountpoint_source = _mapping.source if os.path.isabs(_mapping.source) else \
        #         os.path.join(local_source_path, _mapping.source)
        #     # mountpoint source to pass to docker (depends on rsync)
        #     source_path = _proj.path if not sync_remote else \
        #         os.path.join(RSYNC_DESTINATION_PATH, os.path.abspath(_proj.path).lstrip("/"))
        #     mountpoint_source = _mapping.source if os.path.isabs(_mapping.source) else \
        #         os.path.join(source_path, _mapping.source)
        #     # mountpoint destination (never depends on rsync)
        #     mountpoint_destination = _mapping.destination
        #     # mountpoint mode (i.e., ro, rw, etc)
        #     mode = _mapping.mode
        #     # resolve paths
        #     local_mountpoint_source = str(Path(local_mountpoint_source).resolve())
        #     mountpoint_source = str(Path(mountpoint_source).resolve())
        #     mountpoint_destination = str(Path(mountpoint_destination).resolve())
        #     # make sure we have no conflicts of mountpoints
        #     conflict = mountpoints.get(mountpoint_destination, None)
        #     if conflict not in [None, local_mountpoint_source]:
        #         cpklogger.error(f"Mountpoint '{mountpoint_destination}' inside the container "
        #                         f"wants to be claimed by both '{conflict}' and "
        #                         f"'{local_mountpoint_source}'.")
        #         return False
        #     # compile mounpoints and add them to list
        #     volumes.extend([
        #         "-v", "{:s}:{:s}:{:s}".format(mountpoint_source, mountpoint_destination, mode)
        #     ])
        #     mountpoints[mountpoint_destination] = local_mountpoint_source
        #     # only non-absolute paths can be rsynced
        #     if not os.path.isabs(_mapping.source):
        #         rsync_mountpoints[mountpoint_source] = local_mountpoint_source
        #     # ---
        #     return True

        # mappings
        # for proj in projects_to_mount:
        #     # iterate over list of mappings
        #     for mapping in proj.layers.get("mounts", []):
        #         if len(triggers.intersection(mapping.triggers)) <= 0:
        #             continue
        #         # ---
        #         success = _mount(proj, mapping)
        #         if not success:
        #             return False

        # print out configuration
        cpklogger.debug(f"Container configuration:\n{pretty_json(configuration.compile(project), 4)}")

        # run
        cpklogger.info(f"Running container '{configuration.name}'...")

        try:
            with project.docker.container(machine, configuration):
                pass
        except dockertown.DockerException as e:
            if e.return_code != 0:
                cpklogger.error(f"Container exited with exit code: {e.return_code}")

        if parsed.detach:
            cpklogger.info("Your container is running in detached mode!")


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
