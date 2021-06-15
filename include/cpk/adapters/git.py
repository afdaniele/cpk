from typing import Optional

from .generic import ProjectVersion
from .null import NullAdapter
from ..utils.git import get_repo_info


class GitRepositoryAdapter(NullAdapter):

    def __init__(self, path: str):
        super(GitRepositoryAdapter, self).__init__('git')
        self._path = path
        self._repo = get_repo_info(self._path)
        self.enabled = self._repo.present

    @property
    def name(self) -> str:
        return self._repo.name

    @property
    def organization(self) -> str:
        return self._repo.origin.organization

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
    def maintainer(self) -> Optional[str]:
        # TODO: compile maintainer in the form "First Last (Email)" from git
        return None
