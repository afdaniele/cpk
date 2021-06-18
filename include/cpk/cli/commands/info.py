import argparse
from typing import Optional

import termcolor as tc

from cpk import CPKProject
from .. import AbstractCLICommand
from ..logger import cpklogger
from ...types import Machine, Arguments

PROJECT_INFO = """
{project}
{space} Name: {name}
{space} Tag: {tag}
{space} Version: {version}
{space} Template:
{space}   Name: {template_name}
{space}   Version: {template_version}
{space} Index: {index}
{space} Path: {path}
{space} URL: {url}
{space} Adapters: {adapters}
{end}
"""


class CLIInfoCommand(AbstractCLICommand):

    KEY = 'info'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        return parser

    @staticmethod
    def execute(machine: Optional[Machine], parsed: argparse.Namespace) -> bool:
        cpklogger.info("Project workspace: {}".format(parsed.workdir))

        # get the project
        project = CPKProject(parsed.workdir)

        # index status
        index = tc.colored("Clean", "green") if project.is_clean() \
            else tc.colored("Dirty", "yellow")

        # show info about project
        info = {
            "project": tc.colored("Project:", "grey", "on_white"),
            "name": project.name,
            "tag": project.version.tag,
            "version": project.version.head or "unreleased",
            "template_name": project.template.name,
            "template_version": project.template.version,
            "index": index,
            "path": project.path,
            "url": project.url or "(none)",
            "adapters": " ".join(project.adapters.keys()),
            "space": tc.colored("  ", "grey", "on_white"),
            "end": tc.colored("________", "grey", "on_white"),
        }
        cpklogger.print(PROJECT_INFO.format(**info))

        # ---
        return True
