import argparse
import copy
import json
import os
import re
from distutils.dir_util import copy_tree
from typing import Optional

from cpk.cli.commands.info import CLIInfoCommand
from .. import AbstractCLICommand
from ..logger import cpklogger
from ...types import Machine, Arguments

skel_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "skeleton"))
surgery = {
    "name": {
        "title": "Project Name",
        "targets": ["project.cpk"],
        "pattern": r"^[a-zA-Z0-9-_]+$",
        "pattern_human": "an alphanumeric string [a-zA-Z0-9-_]"
    },
    "description": {
        "title": "Project Description",
        "targets": ["project.cpk"],
        "pattern": r"^.+$",
        "pattern_human": "a non-empty free text"
    },
    "organization": {
        "title": "Owner Username",
        "targets": ["project.cpk"],
        "pattern": r"^[a-zA-Z0-9-_]+$",
        "pattern_human": "an alphanumeric string [a-zA-Z0-9-_]"
    },
    "maintainer": {
        "title": "Owner Full Name",
        "targets": ["project.cpk"],
        "pattern": r"^.+$",
        "pattern_human": "a non-empty string, suggested format is 'First Last <EMail Address>'"
    },
}


class CLICreateCommand(AbstractCLICommand):

    KEY = 'create'

    @staticmethod
    def parser(parent: Optional[argparse.ArgumentParser] = None,
               args: Optional[Arguments] = None) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(parents=[parent])
        parser.add_argument(
            'path',
            help="Location where to create the new project"
        )
        return parser

    @staticmethod
    def execute(machine: Optional[Machine], parsed: argparse.Namespace) -> bool:
        parsed.workdir = os.path.abspath(parsed.path)

        # make sure the path does not exist or it is empty
        if os.path.exists(parsed.workdir) and any(os.scandir(parsed.workdir)):
            cpklogger.error(f"Directory '{parsed.workdir}' is not empty.")
            return False

        # collect info about the new project
        cpklogger.info("Please, provide information about your new project:")
        project_info = {}
        surgery_targets = set()
        print("   |")
        for key in ["name", "description", "organization", "maintainer"]:
            info = surgery[key]
            default = ""
            title = info["title"]
            # suggest a project name given the path name
            if key == "name":
                default = os.path.basename(parsed.workdir)
                title = f"{info['title']} [{default}]"
            # ---
            done = False
            while not done:
                res = input(f"   |\t{title}: ") or default
                if not re.match(info['pattern'], res):
                    cpklogger.error(f"\tField '{info['title']}' must be {info['pattern_human']}.")
                    continue
                done = True
                project_info[key] = res
            surgery_targets.update(info['targets'])

        # make new project
        os.makedirs(parsed.workdir, exist_ok=True)
        cpklogger.info("New Project workspace: {}".format(parsed.workdir))

        # copy skeleton
        cpklogger.debug(f"Creating empty project...")
        copy_tree(skel_dir, parsed.workdir, dry_run=True)
        copy_tree(skel_dir, parsed.workdir)

        # perform surgery
        for target in surgery_targets:
            target_fpath = os.path.join(parsed.workdir, target)
            cpklogger.debug(f"Performing surgery on {target_fpath}...")
            # read target from disk
            with open(target_fpath, "rt") as fin:
                content = json.load(fin)
            # perform surgery
            new_content = copy.deepcopy(content)
            for k, v in content.items():
                if isinstance(v, str):
                    new_content[k] = v.format(**project_info)
            # write target to disk
            with open(target_fpath, "wt") as fout:
                json.dump(new_content, fout, indent=4, sort_keys=True)
        cpklogger.debug("Surgery completed")

        # show info about the new project
        CLIInfoCommand.execute(None, parsed)
        # TODO: add a link to the online docs on how to get started with the new project
        cpklogger.info(f"Your new project was created in '{parsed.workdir}'.")
        # ---
        return True
