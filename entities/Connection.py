from entities import MetadataError
from entities.Hub import Hub
from entities.Metadata import Metadata


class MetadataConnection(Metadata):
    def __init__(self, max_link_capacity: int = 1) -> None:
        if max_link_capacity <= 0:
            raise MetadataError("max_link_capacity must be greater than 0")
        self.attributes = {'max_link_capacity': max_link_capacity}

    def getattributes(self) -> dict:
        return self.attributes


class Connection:
    def __init__(self, hub_from: Hub, hub_to: Hub,
                 metadata: Metadata) -> None:
        self.hub_from = hub_from
        self.hub_to = hub_to
        self.metadata = metadata
        self.drones_this_turn: int = 0

    def reset_turn(self) -> None:
        self.drones_this_turn = 0

    def can_pass(self) -> bool:
        max_capa: int = self.metadata.getattributes().get('max_link_capacity',
                                                          0)
        return self.drones_this_turn < max_capa
