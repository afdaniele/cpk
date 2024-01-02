from .generic import GenericAdapter


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
    def maintainer(self) -> None:
        return None

    @property
    def url(self) -> None:
        return None
