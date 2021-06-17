import argparse

from cpk import CPKProject
from cpk.cli import cpklogger


def check_git_status(project: CPKProject, parsed: argparse.Namespace, must_be_clean: bool = True) \
        -> bool:
    # check if the git HEAD is detached
    if project.is_detached():
        cpklogger.error(
            "The repository HEAD is detached. Create a branch or check one out "
            "before continuing. Aborting."
        )
        return False

    # check if the index is clean
    if project.is_dirty() and must_be_clean:
        cpklogger.warning("Your index is not clean (some files are not committed).")
        cpklogger.warning("If you know what you are doing, use --force (-f) to force.")
        if not parsed.force:
            return False
        cpklogger.warning("Forced!")

    # ---
    return True
