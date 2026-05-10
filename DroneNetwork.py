from typing import Dict, List, Any

from entities import Connection, Drone, Hub, Metadata, MetadataError, HubType
from entities.Hub import MetadataHub


class HubNameError(Exception):
    """Exception raised when a hub name is already in use or cannot be
    found."""
    pass


def can_use_link(connection: Connection) -> Any:
    """
        Checks if a connection link has remaining capacity for the
        current turn.

        Args:
            connection (Connection): The connection to check.

        Returns:
            Any: True if the current load is below max capacity, False
            otherwise.
        """
    return (connection.drones_this_turn <
            connection.metadata.getattributes().get('max_link_capacity', 0))


def can_use_hub(hub: Hub) -> Any:
    """
        Checks if a hub has remaining space to receive another drone.

        Args:
            hub (Hub): The hub to check.

        Returns:
            Any: True if current drones are fewer than max capacity, False
            otherwise.
        """
    return (len(hub.drone_hub.drones) <
            hub.metadata.getattributes().get('max_drones', 0))


def execute_move(drone: Drone, target_hub: Hub, connection: Connection) \
        -> None:
    """
        Performs the physical movement of a drone between two hubs.

        Args:
            drone (Drone): The drone to move.
            target_hub (Hub): The destination hub.
            connection (Connection): The link used for the movement.
        """
    drone.hub.drone_hub.drones.remove(drone)
    drone.hub = target_hub
    target_hub.drone_hub.drones.append(drone)
    connection.drones_this_turn += 1


class DroneNetwork:
    """
        Core engine managing the drone simulation, pathfinding, and state
        history.

        Attributes:
            nb_drones (int): Total number of drones to simulate.
            hubs (Dict[str, Hub]): Map of hub names to Hub objects.
            drones (List[Drone]): List of all drones in the network.
            connections (List[Connection]): List of all bidirectional links.
            history (List[Any]): Recorded drone states per turn.
            history_hub (List[Any]): Recorded hub occupancy per turn.
            history_conn (List[Any]): Recorded connection loads per turn.
        """

    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.hubs: Dict[str, Hub] = {}
        self.drones: List[Drone] = []
        self.connections: List[Connection] = []
        self.history: List[Any] = []
        self.history_hub: List[Any] = []
        self.history_conn: List[Any] = []

    def init_drone(self) -> None:
        """Initializes and places all drones at the START_HUB."""
        start_hub = next(
            (h for h in self.hubs.values() if h.hub_type == HubType.START_HUB),
            None)
        if start_hub is not None:
            for i in range(1, self.nb_drones + 1):
                self.drones.append(Drone(i, start_hub))
        else:
            raise MetadataError("no start hub")

    def add_hub(self, hub: Hub) -> None:
        """Adds a new hub to the network after validating uniqueness and
        coordinates."""
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
        """Creates a bidirectional connection between two named hubs."""
        if name_a not in self.hubs or name_b not in self.hubs:
            raise MetadataError(
                f"Link impossible: {name_a} or {name_b} not existing.")

        hub_a = self.hubs[name_a]
        hub_b = self.hubs[name_b]
        conn = Connection(hub_a, hub_b, meta)
        self.connections.append(conn)
        hub_a.get_connections().append(conn)
        hub_b.get_connections().append(conn)

    def get_shortest_path(self, drone: Drone) -> List[Hub]:
        """
                Calculates the optimal path for a drone using a modified
                Dijkstra algorithm.
                Considers zone costs (restricted/priority) and current
                congestion.

                Returns:
                    List[Hub]: A list of hubs representing the shortest path
                    to the END_HUB.
                """
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
        """Executes a single turn of the simulation, moving all drones
        simultaneously."""
        for hub in self.hubs.values():
            for conn in hub.get_connections():
                conn.reset_turn()

        for drone in self.drones:
            if drone.waiting_time > 0:
                drone.waiting_time -= 1
                if drone.waiting_time == 0:
                    connection = next(c for c in drone.hub.get_connections() if
                                      (c.hub_from == drone.target_hub or
                                       c.hub_to == drone.target_hub) and
                                      (c.hub_to == drone.hub or
                                       c.hub_from == drone.hub))
                    connection.drones_this_turn += 1
                    connection.drones.remove(drone)
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
                              (c.hub_from == next_hub or
                               c.hub_to == next_hub) and
                              (c.hub_to == drone.hub or
                               c.hub_from == drone.hub))

            if (can_use_link(connection) and can_use_hub(next_hub) or
                    next_hub.hub_type == HubType.END_HUB and
                    can_use_link(connection)):

                dest_zone = next_hub.metadata.getattributes()['zone']

                drone.hub.drone_hub.drones.remove(drone)
                connection.drones_this_turn += 1

                if dest_zone == MetadataHub.ZoneType.restricted:
                    drone.waiting_time = 1
                    drone.target_hub = next_hub
                    connection.drones.append(drone)
                else:
                    drone.hub = next_hub
                    drone.hub.drone_hub.drones.append(drone)

    def precalculate_all_turns(self) -> None:
        """Runs the simulation until all drones reach the END_HUB,
        saving states to history."""
        self.save_state()

        while any(
                d.hub.hub_type != HubType.END_HUB
                or d.waiting_time > 0 for d in self.drones):
            self.run_simulation_turn()
            self.save_state()

    def save_state(self) -> None:
        """Captures the current position and status of all entities in the
        history buffers."""
        state = []
        state_hub = []
        state_conn = []
        for d in self.drones:
            state.append({
                "id": d.id,
                "hub_name": d.hub.name if d.hub else None,
                "target_name": d.target_hub.name if d.target_hub else None,
                "waiting": d.waiting_time
            })
        for h in self.hubs.values():
            state_hub.append({
                'name': h.name,
                'max_drones': h.metadata.getattributes()['max_drones'],
                'drone': len(h.drone_hub.drones)
            })
        for con in self.connections:
            state_conn.append({
                'name': f"{con.hub_from.name}-{con.hub_to.name}",
                'max_drones': con.metadata.
                getattributes()['max_link_capacity'],
                'drone': len(con.drones)
            })
        self.history.append(state)
        self.history_hub.append(state_hub)
        self.history_conn.append(state_conn)

    def print_result(self) -> None:
        """Outputs the movement logs to standard output in the required
        format."""
        last_hub: dict = {}
        for i, h in enumerate(self.history):
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
