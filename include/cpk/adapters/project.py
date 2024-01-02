from typing import Optional

import cpk

from .null import NullAdapter
from ..types import Maintainer


class ProjectLayersAdapter(NullAdapter):

    def __init__(self, project: "cpk.CPKProject"):
        super(ProjectLayersAdapter, self).__init__('project')
        self._project = project
        self.enabled = True

    @property
    def name(self) -> str:
        return self._project.layers.self.name

    @property
    def registry(self) -> str:
        return self._project.docker.registry.compile() or "docker.io"

    @property
    def organization(self) -> str:
        return self._project.layers.self.organization

    @property
    def description(self) -> Optional[str]:
        return self._project.layers.self.description

    @property
    def maintainer(self) -> Maintainer:
        return self._project.layers.self.maintainer
