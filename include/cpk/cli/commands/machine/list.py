import argparse
from typing import Optional

from cpk import cpkconfig
from cpk.cli import AbstractCLICommand, cpklogger
from cpk.cli.utils import combine_args
from cpk.types import CPKMachine, Arguments


class CLIMachineListCommand(AbstractCLICommand):

    KEY = 'machine list'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)
        # ---
        return parser

    @staticmethod
    def execute(_: CPKMachine, parsed: argparse.Namespace, **kwargs) -> bool:
        # combine arguments
        parsed = combine_args(parsed, kwargs)
        # ---
        machines = cpkconfig.machines
        if len(machines) == 0:
            cpklogger.info("No machines found")
            return True
        # print table
        cpklogger.info(f"Number of machines found: {len(machines)}")
        table_fmt = "   |    {:<8} {:<15} {:<10} {:<1}"
        print("-" * (8 + 15 + 10 + 40))
        print(table_fmt.format('ID', 'NAME', 'TYPE', 'ENDPOINT'))
        for i, (name, machine) in enumerate(machines.items()):
            print(table_fmt.format(i+1, name, machine.type, machine.base_url))
        print()
        # ---
        return True
