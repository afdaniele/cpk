import argparse
import copy
import logging
import os
import sys

import cpk
from cpk import cpkconfig
from cpk.cli.commands.build import CLIBuildCommand
from cpk.cli.commands.clean import CLICleanCommand
from cpk.cli.commands.create import CLICreateCommand
from cpk.cli.commands.decorate import CLIDecorateCommand
from cpk.cli.commands.endpoint import CLIEndpointCommand
from cpk.cli.commands.info import CLIInfoCommand
from cpk.cli.commands.machine import CLIMachineCommand
from cpk.cli.commands.pull import CLIPullCommand
from cpk.cli.commands.push import CLIPushCommand
from cpk.cli.commands.run import CLIRunCommand
from cpk.cli.logger import cpklogger, update_logger
from cpk.exceptions import CPKException
from cpk.utils.machine import get_machine

_supported_commands = {
    'create': CLICreateCommand,
    'info': CLIInfoCommand,
    'build': CLIBuildCommand,
    'run': CLIRunCommand,
    'clean': CLICleanCommand,
    'push': CLIPushCommand,
    'pull': CLIPullCommand,
    'decorate': CLIDecorateCommand,
    'machine': CLIMachineCommand,
    'endpoint': CLIEndpointCommand,
}


def run():
    cpklogger.info(f"CPK - Code Packaging toolKit - v{cpk.__version__}")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        'command',
        choices=_supported_commands.keys()
    )
    # print help (if needed)
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        parser.print_help()
        return
    # find positional arguments: positional1 is after `--`, positional2 is after `++`
    try:
        pp = sys.argv.index("++")
    except ValueError:
        pp = len(sys.argv)
    try:
        mm = sys.argv.index("--")
    except ValueError:
        mm = len(sys.argv)
    # store arguments
    cpk.cli.arguments.all = copy.copy(sys.argv)
    cpk.cli.arguments.positional1 = sys.argv[mm + 1: len(sys.argv) if pp < mm else pp]
    cpk.cli.arguments.positional2 = sys.argv[pp + 1: len(sys.argv) if mm < pp else mm]
    # remove positional arguments from argv
    sys.argv = sys.argv[0:min(mm, pp)] + ["--"] + cpk.cli.arguments.positional1
    # ---
    # parse `command`
    parsed, remaining = parser.parse_known_args()
    # get command
    command = _supported_commands[parsed.command]
    # let the command parse its arguments
    cmd_parser = command.get_parser(remaining)
    parsed = cmd_parser.parse_args(remaining)
    # sanitize workdir
    parsed.workdir = os.path.abspath(parsed.workdir)
    # enable debug
    if parsed.debug:
        update_logger(logging.DEBUG)
    # get machine
    machine = get_machine(parsed, cpkconfig.machines)
    # avoid commands using `parsed.machine`
    parsed.machine = None
    # execute command
    try:
        with machine:
            res = command.execute(machine, parsed)
        if res is False:
            exit(1)
    except CPKException as e:
        cpklogger.error(str(e))
        exit(2)
    except KeyboardInterrupt:
        cpklogger.info(f"Operation aborted by the user")
        exit(3)


if __name__ == '__main__':
    run()
