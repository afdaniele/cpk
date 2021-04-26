from typing import Optional

from .generic import ProjectVersion
from cpk.types import CPKProjectInfo
from .null import NullAdapter


class ProjectFileAdapter(NullAdapter):

    def __init__(self, info: CPKProjectInfo):
        super(ProjectFileAdapter, self).__init__('project.cpk')
        self._info = info
        self.enabled = True

    @property
    def name(self) -> str:
        return self._info.name

    @property
    def registry(self) -> str:
        return self._info.registry

    @property
    def organization(self) -> str:
        return self._info.organization

    @property
    def description(self) -> Optional[str]:
        return self._info.description

    @property
    def version(self) -> ProjectVersion:
        return ProjectVersion(
            tag=self._info.tag or "latest",
            head=self._info.version or None,
            closest=self._info.version or None,
            sha=None
        )

    @property
    def maintainer(self) -> Optional[str]:
        return self._info.maintainer
