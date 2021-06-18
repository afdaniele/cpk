import argparse
import re
from dataclasses import dataclass
from typing import Optional, Type

from cpk import cpkconfig
from cpk.cli import AbstractCLICommand, cpklogger
from cpk.machine import SSHMachine
from cpk.types import Machine, Arguments


@dataclass
class MachineTarget:
    pattern: str
    explanation: str
    cls: Type[Machine]


_valid_targets = {
    "ssh": MachineTarget(
        pattern=r"^(ssh\:\/\/)?(?P<user>.*?)@(?P<host>[^:]+?)(?::(?P<port>[0-9]+))?$",
        explanation="user@host[:port]",
        cls=SSHMachine
    ),
}


class CLIMachineCreateCommand(AbstractCLICommand):

    KEY = 'machine create'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)
        parser.add_argument(
            'name',
            type=str,
            help="Name to assign to the machine"
        )
        parser.add_argument(
            'target',
            type=str,
            help="Target URI of the machine's endpoint"
        )
        # ---
        return parser

    @staticmethod
    def execute(machine: Machine, parsed: argparse.Namespace) -> bool:
        # validate machine's name
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9\-_.]+[a-zA-Z0-9]$", parsed.name):
            cpklogger.error("Invalid name for a machine. "
                            "Valid characters are: a-z, A-Z, 0-9, -, _\n"
                            "First and last character must be alphanumeric.")
            return False
        # make sure the machine does not exist
        if parsed.name in cpkconfig.machines:
            cpklogger.error("A machine with the same name already exists.")
            return False
        # validate target
        machine = None
        for target_type, target in _valid_targets.items():
            match = re.match(target.pattern, parsed.target)
            if match:
                machine = target.cls(name=parsed.name, **match.groupdict())
                break
        if machine is None:
            cpklogger.error("Invalid target.\nSupported options are:")
            print()
            for target_type, target in _valid_targets.items():
                print(f"\t{target_type}:\t {target.explanation}")
            print()
            return False
        # we have a good machine
        cpklogger.info("Creating machine:")
        print(machine)
        try:
            machine.save(cpklogger)
        except (FileNotFoundError, ValueError) as e:
            cpklogger.error(f"An error occurred while creating the machine. Reason:\n\t{str(e)}")
            machine.remove(cpklogger)
            return False
        except KeyboardInterrupt as e:
            machine.remove(cpklogger)
            raise e
        # ---
        cpklogger.info("Machine successfully created.")
        cpklogger.info("You can now use it with,")
        cpklogger.info(f"\n\t   >  cpk -H {machine.name} ...\n")
