from enum import Enum
from typing import List

from entities import MetadataError
from entities.Metadata import Metadata


class MetadataHub(Metadata):
    class ZoneType(Enum):
        normal = 1
        blocked = 3
        restricted = 2
        priority = 0

    def __init__(self, zone: str = 'normal', color: str = 'None',
                 max_drones: int = 1) -> None:
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
        return self.attributes


class HubType(Enum):
    START_HUB = 1
    HUB = 2
    END_HUB = 3


class Hub:
    class HubDrone:
        def __init__(self) -> None:
            from entities import Drone
            self.drones: List[Drone] = []

    class HubConnection:
        def __init__(self) -> None:
            from entities import Connection
            self.connections: List[Connection] = []

    def __init__(self, hub_type: HubType, name: str, x: int, y: int,
                 metadata: MetadataHub) -> None:
        self.hub_type = hub_type
        self.name = name
        self.x = x
        self.y = y
        self.metadata: Metadata = metadata
        self.connections: Hub.HubConnection = Hub.HubConnection()
        self.drone_hub: Hub.HubDrone = Hub.HubDrone()

    def get_connections(self) -> List:
        return self.connections.connections

    def can_receive_drone(self) -> bool:
        max_allowed: int = self.metadata.getattributes()['max_drones']
        return len(self.drone_hub.drones) < max_allowed
