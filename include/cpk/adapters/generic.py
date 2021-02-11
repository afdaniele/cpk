import getpass
import dataclasses
from typing import Union


@dataclasses.dataclass
class ProjectVersion:
    tag: str
    head: Union[None, str]
    closest: Union[None, str]
    sha: Union[None, str]


class GenericAdapter:

    def __init__(self, adapter_id: str):
        self._id = adapter_id
        self.enabled = False

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> Union[None, str]:
        return None

    @property
    def version(self) -> ProjectVersion:
        return ProjectVersion(
            tag="latest",
            head=None,
            closest=None,
            sha=None
        )

    @property
    def owner(self) -> Union[None, str]:
        return getpass.getuser()

    @property
    def url(self):
        return None

    def __str__(self):
        return self._id
