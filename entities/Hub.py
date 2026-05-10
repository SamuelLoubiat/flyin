from enum import Enum
from typing import List

from entities import MetadataError
from entities.Metadata import Metadata


class MetadataHub(Metadata):
    """
        Handles metadata specific to a Hub (Zone), including terrain and
        capacity.

        Attributes:
            attributes (dict): Dictionary containing zone type, color, and max
            occupancy.
        """

    class ZoneType(Enum):
        """Enumeration of zone types and their relative cost/priority levels.
        """
        normal = 1
        blocked = 3
        restricted = 2
        priority = 0

    def __init__(self, zone: str = 'normal', color: str = 'None',
                 max_drones: int = 1) -> None:
        """
                Initializes the Hub metadata.

                Args:
                    zone (str): The type of zone (e.g., 'normal',
                    'restricted').
                    color (str): Visual representation color for the
                    GUI/Terminal.
                    max_drones (int): Maximum number of drones allowed in the
                    hub.

                Raises:
                    MetadataError: If the zone type is invalid or max_drones
                    is non-positive.
                """
        try:
            meta_zone = MetadataHub.ZoneType[zone.lower()]
        except KeyError:
            raise MetadataError(f"'{zone}' is not a valid zone type")

        if max_drones <= 0:
            raise MetadataError("max_drones must be greater than 0")

        self.attributes = {
            'zone': meta_zone,
            'color': color,
            'max_drones': max_drones
        }

    def getattributes(self) -> dict:
        """Returns the hub's specific attributes."""
        return self.attributes


class HubType(Enum):
    """Enumeration identifying the hub role (Start, Standard, or End)."""
    START_HUB = 1
    HUB = 2
    END_HUB = 3


class Hub:
    """
        Represents a zone (node) in the drone navigation graph.

        Attributes:
            hub_type (HubType): The category of the hub.
            name (str): Unique name of the zone.
            x (int): Horizontal coordinate.
            y (int): Vertical coordinate.
            metadata (Metadata): Associated properties like capacity and zone
            type.
            connections (Hub.HubConnection): Container for outgoing
            connections.
            drone_hub (Hub.HubDrone): Container for drones currently at this
            location.
        """

    class HubDrone:
        """Internal container for managing drones present at this hub."""

        def __init__(self) -> None:
            from entities import Drone
            self.drones: List[Drone] = []

    class HubConnection:
        """Internal container for managing connections linked to this hub."""

        def __init__(self) -> None:
            from entities import Connection
            self.connections: List[Connection] = []

    def __init__(self, hub_type: HubType, name: str, x: int, y: int,
                 metadata: MetadataHub) -> None:
        """Initializes a Hub with its coordinates and physical properties."""
        self.hub_type = hub_type
        self.name = name
        self.x = x
        self.y = y
        self.metadata: Metadata = metadata
        self.connections: Hub.HubConnection = Hub.HubConnection()
        self.drone_hub: Hub.HubDrone = Hub.HubDrone()

    def get_connections(self) -> List:
        """
                Retrieves all connections linked to this hub.

                Returns:
                    List: A list of Connection objects.
                """
        return self.connections.connections

    def can_receive_drone(self) -> bool:
        """
                Retrieves all connections linked to this hub.

                Returns:
                    List: A list of Connection objects.
                """
        max_allowed: int = self.metadata.getattributes()['max_drones']
        return len(self.drone_hub.drones) < max_allowed
