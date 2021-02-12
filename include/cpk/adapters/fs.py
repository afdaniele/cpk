import os

from .generic import GenericAdapter


class FileSystemAdapter(GenericAdapter):

    def __init__(self, path: str):
        super(FileSystemAdapter, self).__init__('fs')
        self._path = path
        self.enabled = True

    @property
    def name(self) -> str:
        return os.path.basename(self._path).lower()
