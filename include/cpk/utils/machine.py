import argparse
import glob
import json
import os
from pathlib import Path
from typing import Dict

import jsonschema

from cpk.cli import cpklogger
from cpk.schemas import get_machine_schema
from cpk.utils.misc import sanitize_hostname

from cpk.machine import Machine, FromEnvMachine, TCPMachine, SSHMachine, UnixSocketMachine

_supported_machines = {
    "ssh": SSHMachine,
    "tcp": TCPMachine,
    "socket": UnixSocketMachine
}


def load_machines(path: str) -> Dict[str, Machine]:
    machines = {}
    # iterate over the machines on disk
    for machine_cfg_fpath in glob.glob(os.path.join(path, '*/config.json')):
        machine_dir = Path(machine_cfg_fpath).parent
        machine_name = machine_dir.stem
        try:
            with open(machine_cfg_fpath, 'rt') as fin:
                try:
                    machine_cfg = json.load(fin)
                except json.decoder.JSONDecodeError as e:
                    raise ValueError(f"Machine descriptor file is not a valid JSON file. "
                                     f"Reason:\n\t{str(e)}")
                # make sure the key 'version' is present
                if "version" not in machine_cfg:
                    raise KeyError("Missing field 'version'.")
                # try reading the schema for this version
                try:
                    schema = get_machine_schema(machine_cfg["version"])
                except FileNotFoundError:
                    raise KeyError(f"Machine descriptor version '{machine_cfg['version']}' "
                                   f"not supported.")
                # validate config file
                try:
                    jsonschema.validate(machine_cfg, schema=schema)
                except jsonschema.exceptions.ValidationError as e:
                    raise ValueError(f"Machine descriptor has a bad format. "
                                     f"Reason:\n\t{str(e.message)}")
                # machine is valid, create object
                machine_cls = _supported_machines[machine_cfg["type"]]
                try:
                    machine = machine_cls(name=machine_name, **machine_cfg["configuration"])
                except TypeError as e:
                    raise ValueError(f"Machine descriptor has a bad format. "
                                     f"Reason:\n\t{str(e)}")
        except (KeyError, ValueError) as e:
            cpklogger.warning(f"An error occurred while loading the machine '{machine_name}', "
                              f"the error reads:\n{str(e)}")
            continue
        # we have loaded a valid machine
        machines[machine_name] = machine
    # ---
    return machines


def get_machine(parsed: argparse.Namespace, machines: Dict[str, Machine]) -> Machine:
    if parsed.machine is None:
        cpklogger.debug("Argument 'parsed.machine' not set. Creating machine from environment.")
        return FromEnvMachine()
    # match machine names against given string
    known_machine = machines.get(str(parsed.machine).strip(), None)
    if known_machine:
        cpklogger.debug(f"Machine '{parsed.machine}' is a known machine. "
                        f"Endpoint: {known_machine.base_url}")
        return known_machine
    # assume it is a hostname or IP address
    cpklogger.debug(f"Machine '{parsed.machine}' is not a known machine. "
                    f"Assuming a resolvable hostname or an IP address was passed.")
    return TCPMachine(parsed.machine, sanitize_hostname(parsed.machine))


