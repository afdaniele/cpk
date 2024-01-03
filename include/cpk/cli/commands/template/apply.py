import argparse
from functools import partial
from typing import Optional, Callable

import questionary

from cpk import CPKProject, CPKTemplate

from cpk.cli import AbstractCLICommand, cpklogger
from cpk.template import CPKProjectDiff
from cpk.types import CPKMachine, Arguments


class CLITemplateApplyCommand(AbstractCLICommand):

    KEY = 'template apply'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        # create child parser
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)
        # add arguments
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Do not apply the template, just print the differences."
        )
        # ---
        return parser

    @staticmethod
    def execute(_: CPKMachine, parsed: argparse.Namespace) -> bool:
        # get project
        project = CPKProject(parsed.workdir)
        # get template
        template: Optional[CPKTemplate] = project.fetch_template()
        # exit if the project does not have a template
        if template is None:
            cpklogger.info("This project does not define a template. Nothing to do.")
            return True
        # compute diff
        diff: CPKProjectDiff = template.diff(project)
        # print diff
        color: Callable[[str], str] = lambda c, x: f"\033[{c}m{x}\033[0m"
        red: Callable[[str], str] = partial(color, "31")
        orange: Callable[[str], str] = partial(color, "33")
        white: Callable[[str], str] = partial(color, "37")
        blue: Callable[[str], str] = partial(color, "34")
        # ---
        print(f"Comparing Template:{white(diff.left)} with Project:{white(diff.right)}")
        # ---
        # make sure there is something to do
        if not diff.files_changed and not diff.template_only:
            cpklogger.info("No changes detected. Nothing to do.")
            return True
        # ---
        sep: str = "\n\t- "
        # - different files
        if diff.files_changed:
            print(f"\nThe following files will be overwritten:"
                  f"{blue(f'{sep}{sep.join(diff.files_changed)}')}")
        # - missing files
        if diff.template_only:
            print(f"\nThe following files and directories will be created:"
                  f"{red(f'{sep}{sep.join(diff.template_only)}')}")
        # ask the user if they want to proceed
        warnings: str = "\n" + "-" * 32 + orange("\n".join([
            "",
            "WARNING: This operation will overwrite the files listed above.",
            "         - If you have local uncommitted changes, they will be lost.",
            "         - If you want to keep them, please commit them first.",
            "         - Unless you are using a version control system, you will not be able to recover them."
        ]))
        print(warnings)
        if questionary.confirm(f"Proceed?").ask():
            # apply template
            diff.apply(dry_run=parsed.dry_run)
            if parsed.dry_run:
                cpklogger.info("Template applied in dry-run mode.")
            else:
                cpklogger.info("Template applied successfully!")
        else:
            cpklogger.info("Template application aborted.")
