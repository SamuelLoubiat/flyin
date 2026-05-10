from typing import Dict, List, Any

from entities import Connection, Drone, Hub, Metadata, MetadataError, HubType
from entities.Hub import MetadataHub


class HubNameError(Exception):
    pass


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


class DroneNetwork:

    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.hubs: Dict[str, Hub] = {}
        self.drones: List[Drone] = []
        self.history: List[Any] = []

    def init_drone(self) -> None:
        start_hub = next(
            (h for h in self.hubs.values() if h.hub_type == HubType.START_HUB),
            None)
        if start_hub is not None:
            for i in range(1, self.nb_drones + 1):
                self.drones.append(Drone(i, start_hub))
        else:
            raise MetadataError("no start hub")

    def add_hub(self, hub: Hub) -> None:
        if hub.name in self.hubs:
            raise HubNameError(hub.name)

        for existing in self.hubs.values():
            if existing.x == hub.x and existing.y == hub.y:
                raise MetadataError(
                    f"X and Y ({hub.x}, {hub.y}) is already occupied by"
                    f" '{existing.name}'.")

        if hub.hub_type == HubType.START_HUB:
            if any(
                    h.hub_type == HubType.START_HUB for h in self.hubs.values()
            ):
                raise MetadataError("Only one START_HUB is authorized.")

        if hub.hub_type == HubType.END_HUB:
            if any(h.hub_type == HubType.END_HUB for h in self.hubs.values()):
                raise MetadataError("Only one END_HUB is authorized.")

        self.hubs[hub.name] = hub

    def add_connection(self, name_a: str, name_b: str,
                       meta: Metadata) -> None:
        if name_a not in self.hubs or name_b not in self.hubs:
            raise MetadataError(
                f"Link impossible: {name_a} or {name_b} not existing.")

        hub_a = self.hubs[name_a]
        hub_b = self.hubs[name_b]
        conn = Connection(hub_a, hub_b, meta)
        hub_a.get_connections().append(conn)
        hub_b.get_connections().append(conn)

    def get_shortest_path(self, drone: Drone) -> List[Hub]:
        start_hub = drone.hub
        end_hub = next(
            (h for h in self.hubs.values() if h.hub_type == HubType.END_HUB),
            None)

        if not start_hub or not end_hub:
            return []

        distances = {name: float('inf') for name in self.hubs}
        distances[start_hub.name] = 0
        previous_hubs: dict[str, Hub | None] = \
            {name: None for name in self.hubs}
        unvisited = list(self.hubs.keys())

        while unvisited:
            curr_name = min(unvisited, key=lambda n: distances[n])
            if distances[curr_name] == float('inf'):
                break

            curr_hub: Hub = self.hubs[curr_name]
            unvisited.remove(curr_name)
            if curr_hub == end_hub:
                break

            for conn in curr_hub.get_connections():
                neighbor = conn.hub_to if conn.hub_from == curr_hub \
                    else conn.hub_from
                if neighbor.name not in unvisited:
                    continue

                z_type = neighbor.metadata.getattributes()['zone']
                if z_type == MetadataHub.ZoneType.restricted:
                    cost = 2.0
                elif z_type == MetadataHub.ZoneType.blocked:
                    cost = 999.0
                elif z_type == MetadataHub.ZoneType.priority:
                    cost = 0.5
                else:
                    cost = 1.0

                cost += len(neighbor.drone_hub.drones)

                if distances[curr_name] + cost < distances[neighbor.name]:
                    distances[neighbor.name] = distances[curr_name] + cost
                    previous_hubs[neighbor.name] = curr_hub
        path = []
        curr: Hub | None = end_hub
        if distances[end_hub.name] == float('inf'):
            return []
        while curr is not None:
            path.append(curr)
            curr = previous_hubs[curr.name]
        return path[::-1]

    def run_simulation_turn(self) -> None:
        for hub in self.hubs.values():
            for conn in hub.get_connections():
                conn.reset_turn()

        for drone in self.drones:
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

            path = self.get_shortest_path(drone)
            if len(path) < 2:
                continue

            next_hub = path[1]

            connection = next(c for c in drone.hub.get_connections() if
                              (c.hub_from == drone.hub or
                               c.hub_to == next_hub))

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

    def precalculate_all_turns(self) -> None:

        self.save_state()

        max_turns = 1000
        turn_count = 0
        while any(
                d.hub.hub_type != HubType.END_HUB
                or d.waiting_time > 0 for d in self.drones):
            self.run_simulation_turn()
            self.save_state()
            turn_count += 1
            if turn_count >= max_turns:
                break

    def save_state(self) -> None:
        state = []
        for d in self.drones:
            state.append({
                "id": d.id,
                "hub_name": d.hub.name if d.hub else None,
                "target_name": d.target_hub.name if d.target_hub else None,
                "waiting": d.waiting_time
            })
        self.history.append(state)

    def print_result(self) -> None:
        last_hub: dict = {}
        for h in self.history:
            data = ""
            for s in h:
                if last_hub.get(s['id']) is None:
                    last_hub.update({s['id']: s['hub_name']})
                    continue
                if s['target_name'] is None and s['waiting'] == 0:
                    if last_hub.get(s['id']) != s['hub_name']:
                        last_hub.update({s['id']: s['hub_name']})
                        data += f"D{s['id']}-{s['hub_name']} "
            print(data)
