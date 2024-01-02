from typing import Optional

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
    def maintainer(self) -> Optional[str]:
        # TODO: compile maintainer in the form "First Last (Email)" from git
        return None
