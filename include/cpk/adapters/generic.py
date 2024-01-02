import getpass
import os
from typing import Optional


class GenericAdapter:

    def __init__(self, adapter_id: str):
        self._id = adapter_id
        self.enabled = False

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return "project"

    @property
    def registry(self) -> str:
        return os.environ.get("DOCKER_REGISTRY", "docker.io")

    @property
    def organization(self) -> str:
        return getpass.getuser()

    @property
    def description(self) -> Optional[str]:
        return None

    @property
    def maintainer(self) -> str:
        return getpass.getuser()

    @property
    def url(self) -> Optional[str]:
        return None

    def __str__(self) -> str:
        return self._id
