from typing import Any

from Entities import DroneNetwork
from entities import Hub, HubType, Drone, Connection, MetadataError
from entities.Hub import MetadataHub


def run_simulation_turn(dn: DroneNetwork) -> None:
    for hub in dn.hubs.values():
        for conn in hub.get_connections():
            conn.reset_turn()

    for drone in dn.drones:
        if drone.waiting_time > 0:
            drone.waiting_time -= 1
            if drone.waiting_time == 0:
                connection = next(c for c in drone.hub.get_connections() if
                                  (c.hub_from == drone.target_hub or
                                   c.hub_to == drone.target_hub))
                connection.drones_this_turn += 1
                if drone.target_hub is not None:
                    drone.hub = drone.target_hub
                else:
                    raise MetadataError("target hub was not set")
                drone.hub.drone_hub.drones.append(drone)
                drone.target_hub = None
            continue

        if drone.hub.hub_type == HubType.END_HUB:
            continue

        path = dn.get_shortest_path(drone)
        if len(path) < 2:
            continue

        next_hub = path[1]

        connection = next(c for c in drone.hub.get_connections() if
                          (c.hub_from == drone.hub or c.hub_to == next_hub))

        if (can_use_link(connection) and can_use_hub(next_hub) or
                next_hub.hub_type == HubType.END_HUB and
                can_use_link(connection)):

            dest_zone = next_hub.metadata.getattributes()['zone']

            drone.hub.drone_hub.drones.remove(drone)
            connection.drones_this_turn += 1

            if dest_zone == MetadataHub.ZoneType.restricted:
                drone.waiting_time = 1
                drone.target_hub = next_hub
            else:
                drone.hub = next_hub
                drone.hub.drone_hub.drones.append(drone)


def can_use_link(connection: Connection) -> Any:
    return (connection.drones_this_turn <
            connection.metadata.getattributes().get('max_link_capacity', 0))


def can_use_hub(hub: Hub) -> Any:
    return (len(hub.drone_hub.drones) <
            hub.metadata.getattributes().get('max_drones', 0))


def execute_move(drone: Drone, target_hub: Hub, connection: Connection) \
        -> None:
    drone.hub.drone_hub.drones.remove(drone)
    drone.hub = target_hub
    target_hub.drone_hub.drones.append(drone)
    connection.drones_this_turn += 1
