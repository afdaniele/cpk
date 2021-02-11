import os
from typing import Union

from .generic import GenericAdapter


class FileSystemAdapter(GenericAdapter):

    def __init__(self, path: str):
        super(FileSystemAdapter, self).__init__('fs')
        self._path = path
        self.enabled = True

    @property
    def name(self) -> Union[None, str]:
        return os.path.basename(self._path).lower()
