import argparse
from typing import Optional

import termcolor as tc

from cpk import CPKProject
from .. import AbstractCLICommand
from ..logger import cpklogger
from ..utils import combine_args, as_table
from ...types import CPKMachine, Arguments


class CLIInfoCommand(AbstractCLICommand):

    KEY = 'info'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        return parser

    @staticmethod
    def execute(machine: Optional[CPKMachine], parsed: argparse.Namespace, **kwargs) -> bool:
        # combine arguments
        parsed = combine_args(parsed, kwargs)
        # ---
        cpklogger.info("Project workspace: {}".format(parsed.workdir))

        # get the project
        project = CPKProject(parsed.workdir)

        # index status
        index = tc.colored("Clean", "green") if project.is_clean() \
            else tc.colored("Dirty", "yellow")

        # show info about project
        info: dict = {
            "Name": project.name,
            "Distribution": project.layers.self.distribution or "ND",
            "Version": project.repository.version.head or "unreleased",
            "Template": project.layers.template.compact if project.layers.template else "ND",
            "Index": index,
            "Path": project.path,
            "URL": project.url or "ND",
        }
        print(as_table(info, "Project Info"))
        # ---
        return True
