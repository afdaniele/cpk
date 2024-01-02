import argparse
from typing import Optional

from .null import NullAdapter


class CLIAdapter(NullAdapter):

    def __init__(self, parsed: Optional[argparse.Namespace]):
        super(CLIAdapter, self).__init__('cli')
        self._parsed = parsed
        self.enabled = parsed is not None
