import ipaddress
import logging
import os
import subprocess
from pathlib import Path
from typing import Union, Optional

import docker
import yaml
from docker.errors import ContainerError, ImageNotFound, APIError

from cpk.constants import CANONICAL_ARCH, CONTAINER_LABEL_DOMAIN, BUILD_COMPATIBILITY_MAP


def run_cmd(cmd):
    cmd = " ".join(cmd)
    lines = subprocess.check_output(cmd, shell=True).decode("utf-8").split("\n")
    return list(filter(lambda line: len(line) > 0, lines))


def assert_canonical_arch(arch):
    if arch not in CANONICAL_ARCH.values():
        raise ValueError(
            f"Given architecture {arch} is not supported. "
            f"Valid choices are: {', '.join(list(set(CANONICAL_ARCH.values())))}"
        )


def canonical_arch(arch):
    if arch not in CANONICAL_ARCH:
        raise ValueError(
            f"Given architecture {arch} is not supported. "
            f"Valid choices are: {', '.join(list(set(CANONICAL_ARCH.values())))}"
        )
    # ---
    return CANONICAL_ARCH[arch]


def cpk_label(key, value=None):
    label = f"{CONTAINER_LABEL_DOMAIN}.{key.lstrip('.')}"
    if value is not None:
        label = f"{label}={value}"
    return label


def sanitize_hostname(hostname: str) -> str:
    try:
        ipaddress.ip_address(hostname)
        return hostname
    except ValueError:
        return f"{hostname}.local" if "." not in hostname else hostname


def parse_configurations(config_file: str) -> dict:
    with open(config_file, "rt") as fin:
        configurations_content = yaml.load(fin, Loader=yaml.SafeLoader)
    if "version" not in configurations_content:
        raise ValueError("The configurations file must have a root key 'version'.")
    # TODO: handle configuration schemas properly (i.e., using JSON/XML schemas)
    if configurations_content["version"] == "1.0":
        return configurations_content["configurations"]


def configure_binfmt(machine_arch: str, arch: str, epoint: docker.DockerClient, logger):
    compatible_archs = BUILD_COMPATIBILITY_MAP[machine_arch]
    if arch not in compatible_archs:
        logger.info("Configuring machine for multiarch...")
        try:
            epoint.containers.run(
                "multiarch/qemu-user-static:register",
                remove=True,
                privileged=True,
                command="--reset",
            )
            logger.info("Multiarch Enabled!")
        except (ContainerError, ImageNotFound, APIError) as e:
            msg = "Multiarch cannot be enabled on the target machine. " \
                  "This might create issues."
            logger.warning(msg)
            logger.debug(f"The error reads:\n\t{str(e)}\n")
    else:
        msg = "Working with an `{}` image on `{}`. Multiarch not needed!".format(
            arch, machine_arch
        )
        logger.info(msg)


def human_size(value: Union[int, float], suffix: str = "B", precision: int = 2):
    fmt = f"%3.{precision}f %s%s"
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(value) < 1024.0:
            return fmt % (value, unit, suffix)
        value /= 1024.0
    return fmt.format(value, "Yi", suffix)


def human_time(time_secs: Union[int, float], compact: bool = False):
    label = lambda s: s[0] if compact else " " + s
    days = int(time_secs // 86400)
    hours = int(time_secs // 3600 % 24)
    minutes = int(time_secs // 60 % 60)
    seconds = int(time_secs % 60)
    parts = []
    if days > 0:
        parts.append("{}{}".format(days, label("days")))
    if days > 0 or hours > 0:
        parts.append("{}{}".format(hours, label("hours")))
    if days > 0 or hours > 0 or minutes > 0:
        parts.append("{}{}".format(minutes, label("minutes")))
    parts.append("{}{}".format(seconds, label("seconds")))
    return ", ".join(parts)


def configure_ssh_for_cpk(logger: Optional[logging.Logger] = None):
    from cpk import cpkconfig
    user_home = Path.home()
    # create .cpk/ssh pool directory if it does not exist
    cpk_ssh_pool_dir = os.path.join(cpkconfig.path, "ssh")
    if logger:
        logger.debug(f"Creating directory '{cpk_ssh_pool_dir}'...")
        if os.path.exists(cpk_ssh_pool_dir):
            logger.debug(f"Directory '{cpk_ssh_pool_dir}' already exists, skipping.")
    os.makedirs(cpk_ssh_pool_dir, mode=0o700, exist_ok=True)
    # create .ssh dir if it does not exist
    ssh_fpath = os.path.join(user_home, ".ssh")
    if logger:
        logger.debug(f"Creating directory '{ssh_fpath}'...")
        if os.path.exists(ssh_fpath):
            logger.debug(f"Directory '{ssh_fpath}' already exists, skipping.")
    os.makedirs(ssh_fpath, mode=0o700, exist_ok=True)
    # read config file
    ssh_config_fpath = os.path.join(ssh_fpath, "config")
    ssh_config = []
    if os.path.isfile(ssh_config_fpath):
        if logger:
            logger.debug(f"Reading SSH configuration file '{ssh_config_fpath}'...")
        with open(ssh_config_fpath, "rt") as fin:
            ssh_config = fin.readlines()
    else:
        if logger:
            logger.debug(f"SSH configuration file '{ssh_config_fpath}' not found. Creating one...")
    # check if it is already configured
    found = False
    include_line = f"Include {os.path.join(cpk_ssh_pool_dir, '*')}"
    for line in ssh_config:
        if line.strip() == include_line:
            found = True
    if found:
        if logger:
            logger.debug(f"User SSH environment already configured for CPK.")
        return
    # add Include statement to the beginning of the file
    ssh_config = [
        "# SSH configuration for cpk (https://github.com/afdaniele/cpk)\n",
        f"{include_line}\n\n\n"
    ] + ssh_config
    # write ssh config file back to disk
    with open(ssh_config_fpath, "wt") as fout:
        if logger:
            logger.debug(f"Writing to SSH configuration file '{ssh_config_fpath}'...")
        fout.writelines(ssh_config)
        if logger:
            logger.debug(f"SSH configuration file '{ssh_config_fpath}' configured for CPK.")


def ask_confirmation(logger, message, default="y", question="Do you confirm?", choices=None):
    binary_question = False
    if choices is None:
        choices = {"y": "Yes", "n": "No"}
        binary_question = True
    choices_str = " ({})".format(", ".join([f"{k}={v}" for k, v in choices.items()]))
    default_str = f" [{default}]" if default else ""
    while True:
        logger.warn(f"{message.rstrip('.')}.")
        r = input(f"{question}{choices_str}{default_str}: ")
        if r.strip() == "":
            r = default
        r = r.strip().lower()
        if binary_question:
            if r in ["y", "yes", "yup", "yep", "si", "aye"]:
                return True
            elif r in ["n", "no", "nope", "nay"]:
                return False
        else:
            if r in choices:
                return r
