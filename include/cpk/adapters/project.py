from typing import Union

from .generic import GenericAdapter, ProjectVersion
from cpk.types import CPKProjectInfo


class ProjectFileAdapter(GenericAdapter):

    def __init__(self, info: CPKProjectInfo):
        super(ProjectFileAdapter, self).__init__('project.cpk')
        self._info = info
        self.enabled = True

    @property
    def name(self) -> str:
        return self._info.name

    @property
    def organization(self) -> str:
        return self._info.organization or super(ProjectFileAdapter, self).organization

    @property
    def description(self) -> Union[None, str]:
        return self._info.description

    @property
    def version(self) -> ProjectVersion:
        return ProjectVersion(
            tag=self._info.tag or super(ProjectFileAdapter, self).version.tag,
            head=self._info.version or super(ProjectFileAdapter, self).version.head,
            closest=self._info.version or super(ProjectFileAdapter, self).version.closest,
            sha=None
        )

    @property
    def maintainer(self) -> Union[None, str]:
        return self._info.maintainer or super(ProjectFileAdapter, self).maintainer
