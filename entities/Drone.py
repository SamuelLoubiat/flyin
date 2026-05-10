from entities.Hub import Hub


class Drone:
    """
        Represents an autonomous unit navigating through the network.

        Attributes:
            id (int): Unique drone identifier.
            hub (Hub): The current hub where the drone is located.
            waiting_time (int): Remaining turns to wait (used for restricted
            zones).
            target_hub (Hub | None): The hub the drone is currently moving
            toward.
        """

    def __init__(self, drone_id: int, hub: Hub):
        """
                Initializes a drone at a starting hub.

                Args:
                    drone_id (int): Unique ID.
                    hub (Hub): Initial Hub (Start Zone).
                """
        self.id: int = drone_id
        self.hub: Hub = hub
        self.waiting_time: int = 0
        self.target_hub: Hub | None = None
        hub.drone_hub.drones.append(self)

    def set_hub(self, hub: Hub) -> None:
        """
                Updates the drone's location to a new hub.

                Args:
                    hub (Hub): The new destination hub.
                """
        self.hub = hub
