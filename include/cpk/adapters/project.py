from typing import Union

from .generic import GenericAdapter, ProjectVersion
from cpk.types import CPKProjectInfo


class ProjectFileAdapter(GenericAdapter):

    def __init__(self, info: CPKProjectInfo):
        super(ProjectFileAdapter, self).__init__('project.cpk')
        self._info = info
        self.enabled = True

    @property
    def name(self) -> Union[None, str]:
        return self._info.name

    @property
    def version(self) -> ProjectVersion:
        return ProjectVersion(
            tag=self._info.tag or super(ProjectFileAdapter, self).version.tag,
            head=self._info.version or super(ProjectFileAdapter, self).version.head,
            closest=self._info.version or super(ProjectFileAdapter, self).version.closest,
            sha=None
        )

    @property
    def owner(self) -> Union[None, str]:
        return self._info.owner or super(ProjectFileAdapter, self).owner
