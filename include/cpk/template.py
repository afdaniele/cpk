import os
import shutil
import subprocess
import tempfile
from filecmp import dircmp
from functools import partial, lru_cache
from typing import Optional, List, Callable, AnyStr

from cpk import CPKProject
from .types import CPKProjectTemplateLayer


Command = List[str]


class CPKTemplate(CPKProject):

    def __init__(self, template: CPKProjectTemplateLayer, tmp_dir: Optional[str] = None):
        # temporary templates directory
        tmp_dir = tmp_dir if tmp_dir else tempfile.gettempdir()
        cpk_templates_dir: str = os.path.join(tmp_dir, "cpk", "templates")
        os.makedirs(cpk_templates_dir, exist_ok=True)
        # create template destination directory
        path: str = os.path.join(cpk_templates_dir, template.provider, template.organization, template.name,
                                 template.version)
        os.makedirs(path, exist_ok=True)
        # download if the directory is empty, update otherwise
        if len(os.listdir(path)) > 0:
            # update (git pull)
            git_pull: Command = ["git", "pull"]
            subprocess.run(git_pull, cwd=path, stdout=subprocess.PIPE)
        else:
            # download (git clone)
            git_clone: Command = ["git", "clone", "--branch", template.version, template.git_url, path]
            subprocess.run(git_clone, stdout=subprocess.PIPE)
        # create template project
        super(CPKTemplate, self).__init__(path=path)

    @property
    def template(self) -> Optional['CPKTemplate']:
        return None

    def diff(self, project: CPKProject) -> 'CPKProjectDiff':
        return CPKProjectDiff(self.path, project.path, ignore=[".git", "cpk/self.yaml"])


class CPKProjectDiff(dircmp):

    @classmethod
    def _extend(cls, _prefix: str, _items: List[AnyStr], _subdir: dircmp, _kind: str, _ignore: List[AnyStr]):
        _items.extend([
            f"{_prefix}{item}" for item in getattr(_subdir, _kind) if f"{_prefix}{item}" not in _ignore
        ])
        for _subsubdir_name, _subsubdir in _subdir.subdirs.items():
            cls._extend(f"{_prefix}{_subsubdir_name}/", _items, _subsubdir, _kind, _ignore)

    @property
    @lru_cache
    def template_only(self) -> List[AnyStr]:
        items: List[AnyStr] = []
        self._extend("", items, self, "left_only", list(self.ignore))
        return items

    @property
    @lru_cache
    def project_only(self) -> List[AnyStr]:
        items: List[AnyStr] = []
        self._extend("", items, self, "right_only", list(self.ignore))
        return items

    @property
    @lru_cache
    def files_changed(self) -> List[AnyStr]:
        items: List[AnyStr] = []
        self._extend("", items, self, "diff_files", list(self.ignore))
        return items

    def print_report(self, colored: bool = True, print_identical: bool = False):
        color: Callable[[str], str] = lambda c, x: x if not colored else f"\033[{c}m{x}\033[0m"
        green: Callable[[str], str] = partial(color, "32")
        red: Callable[[str], str] = partial(color, "31")
        white: Callable[[str], str] = partial(color, "37")
        blue: Callable[[str], str] = partial(color, "34")
        # ---
        print(f"Comparing Template:{white(self.left)} with Project:{white(self.right)}")
        # ---
        sep: str = "\n\t- "
        # identical files
        if print_identical and self.same_files:
            print(f"\nIdentical files:{green(f'{sep}{sep.join(self.same_files)}')}")
        # different files
        if self.files_changed:
            print(f"\nChanges detected:{blue(f'{sep}{sep.join(self.files_changed)}')}")
        # missing files
        if self.template_only:
            print(
                f"\nMissing items from {white('Template')}:" +
                red(f"{sep}{sep.join(self.template_only)}")
            )
        # extra files
        if self.project_only:
            print(
                f"\nExtra items only in {white('Project')}:" +
                green(f"{sep}{sep.join(self.project_only)}")
            )

    def apply(self, dry_run: bool = False):
        # copy files from template to project
        for file in self.template_only:
            src: str = os.path.join(self.left, file)
            dst: str = os.path.join(self.right, file)
            # copy file
            if dry_run:
                print(f"Would copy {src} -> {dst}")
            else:
                if os.path.isdir(src):
                    print(f"Copying directory {src} -> {dst}")
                    shutil.copytree(src, dst)
                else:
                    print(f"Copying file {src} -> {dst}")
                    shutil.copyfile(src, dst)
        # update files in project
        for file in self.files_changed:
            src: str = os.path.join(self.left, file)
            dst: str = os.path.join(self.right, file)
            # copy file
            if dry_run:
                print(f"Would copy {src} -> {dst}")
            else:
                if os.path.isdir(src):
                    print(f"Copying directory {src} -> {dst}")
                    shutil.copytree(src, dst)
                else:
                    print(f"Copying file {src} -> {dst}")
                    shutil.copyfile(src, dst)
