import getpass
from typing import Union

from .generic import GenericAdapter, ProjectVersion
from ..utils.git import get_repo_info


class GitRepositoryAdapter(GenericAdapter):

    def __init__(self, path: str):
        super(GitRepositoryAdapter, self).__init__('git')
        self._path = path
        self._repo = get_repo_info(self._path)
        self.enabled = self._repo.present

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> Union[None, str]:
        return None

    @property
    def version(self) -> ProjectVersion:
        if not self.enabled:
            return super(GitRepositoryAdapter, self).version
        # ---
        return ProjectVersion(
            tag=self._repo.branch,
            head=self._repo.version.head,
            closest=self._repo.version.closest,
            sha=self._repo.sha
        )

    @property
    def owner(self) -> Union[None, str]:
        return getpass.getuser()
