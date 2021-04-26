from .generic import GenericAdapter, ProjectVersion


class NullAdapter(GenericAdapter):

    def __init__(self, adapter_id: str):
        super(NullAdapter, self).__init__(adapter_id)
        self.enabled = True

    @property
    def name(self) -> None:
        return None

    @property
    def registry(self) -> None:
        return None

    @property
    def organization(self) -> None:
        return None

    @property
    def description(self) -> None:
        return None

    @property
    def version(self) -> ProjectVersion:
        return super(NullAdapter, self).version

    @property
    def maintainer(self) -> None:
        return None

    @property
    def url(self) -> None:
        return None
