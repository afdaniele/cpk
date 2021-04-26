import argparse
import sys

from cpk.exceptions import CPKException

from cpk.cli.logger import cpklogger
from cpk.cli.commands.info import CLIInfoCommand
from cpk.cli.commands.build import CLIBuildCommand
from cpk.cli.commands.run import CLIRunCommand
from cpk.cli.commands.clean import CLICleanCommand
from cpk.cli.commands.push import CLIPushCommand
from cpk.cli.commands.decorate import CLIDecorateCommand

_supported_commands = {
    'info': CLIInfoCommand,
    'build': CLIBuildCommand,
    'run': CLIRunCommand,
    'clean': CLICleanCommand,
    'push': CLIPushCommand,
    'decorate': CLIDecorateCommand,
}


def run():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        'command',
        choices=_supported_commands.keys(),
        nargs=1
    )
    # print help (if needed)
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        parser.print_help()
        return
    # ---
    parsed, remaining = parser.parse_known_args()
    # get command
    command_name = parsed.command[0]
    command = _supported_commands[command_name]
    # let the command parse its arguments
    parsed = command.parse_arguments(remaining)
    # execute command
    try:
        command.execute(parsed)
    except CPKException as e:
        cpklogger.error(str(e))


if __name__ == '__main__':
    run()
