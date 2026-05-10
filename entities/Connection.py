from typing import List

from entities import MetadataError
from entities.Drone import Drone
from entities.Hub import Hub
from entities.Metadata import Metadata


class MetadataConnection(Metadata):
    """
        Handles metadata specific to a connection, primarily link throughput.

        Attributes:
            attributes (dict): Dictionary containing link capacity.
        """

    def __init__(self, max_link_capacity: int = 1) -> None:
        """
                Initializes connection metadata.

                Args:
                    max_link_capacity (int): Max drones allowed on this link
                    per turn.

                Raises:
                    MetadataError: If capacity is less than or equal to 0.
                """
        if max_link_capacity <= 0:
            raise MetadataError("max_link_capacity must be greater than 0")
        self.attributes = {'max_link_capacity': max_link_capacity}

    def getattributes(self) -> dict:
        """Returns the connection's specific attributes."""
        return self.attributes


class Connection:
    """
        Represents a bidirectional link between two Hubs.

        Attributes:
            hub_from (Hub): The source hub.
            hub_to (Hub): The destination hub.
            metadata (Metadata): Connection properties (e.g., throughput).
            drones (List[Drone]): Drones currently traversing the link.
            drones_this_turn (int): Counter for drones that used this link
            this turn.
        """

    def __init__(self, hub_from: Hub, hub_to: Hub,
                 metadata: Metadata) -> None:
        """Initializes a link between two hubs."""
        self.hub_from = hub_from
        self.hub_to = hub_to
        self.metadata = metadata
        self.drones: List[Drone] = []
        self.drones_this_turn: int = 0

    def reset_turn(self) -> None:
        """Resets the link's usage counter for a new simulation turn."""
        self.drones_this_turn = 0

    def can_pass(self) -> bool:
        """
                Checks if the link capacity for the current turn has been
                reached.

                Returns:
                    bool: True if more drones can traverse this turn, False
                    otherwise.
                """
        max_capa: int = self.metadata.getattributes().get('max_link_capacity',
                                                          0)
        return self.drones_this_turn < max_capa
