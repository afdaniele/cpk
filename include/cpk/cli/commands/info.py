import argparse
from typing import Optional

import termcolor as tc

from cpk import CPKProject
from .. import AbstractCLICommand
from ..logger import cpklogger
from ..utils import combine_args
from ...types import CPKMachine, Arguments

w = "\033[37m"
x = "\033[0m"

PROJECT_INFO = f"""
----------- Project Info -----------
  {w}Name:{x} {{name}}
  {w}Distibution:{x} {{distribution}}
  {w}Version:{x} {{version}}
  {w}Template:{x} {{template}}
  {w}Index:{x} {{index}}
  {w}Path:{x} {{path}}
  {w}URL:{x} {{url}}
------------------------------------"""


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
        info = {
            "name": project.name,
            "distribution": project.layers.self.distribution or "ND",
            "version": project.repository.version.head or "unreleased",
            "template": project.layers.template.compact if project.layers.template else "ND",
            "index": index,
            "path": project.path,
            "url": project.url or "ND",
        }
        print(PROJECT_INFO.format(**info))
        # ---
        return True
