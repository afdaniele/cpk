import argparse
from typing import Optional

from cpk import CPKProject, CPKTemplate

from cpk.cli import AbstractCLICommand, cpklogger
from cpk.template import CPKProjectDiff
from cpk.types import CPKMachine, Arguments


class CLITemplateDiffCommand(AbstractCLICommand):

    KEY = 'template diff'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        # create child parser
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)
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
        diff.print_report()
