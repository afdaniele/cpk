import argparse
from typing import Optional

from .generic import ProjectVersion
from .null import NullAdapter


class CLIAdapter(NullAdapter):

    def __init__(self, parsed: Optional[argparse.Namespace]):
        super(CLIAdapter, self).__init__('cli')
        self._parsed = parsed
        self.enabled = parsed is not None

    @property
    def version(self) -> Optional[ProjectVersion]:
        if not self.enabled or not hasattr(self._parsed, 'tag') or self._parsed.tag is None:
            return None
        # ---
        return ProjectVersion(
            tag=self._parsed.tag,
            head=None,
            closest=None,
            sha=None
        ) if hasattr(self._parsed, 'tag') else None
