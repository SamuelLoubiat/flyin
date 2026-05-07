from entities.Hub import Hub


class Drone:

    def __init__(self, drone_id: int, hub: Hub):
        self.id: int = drone_id
        self.hub: Hub = hub
        self.waiting_time: int = 0
        self.target_hub: Hub | None = None
        hub.drone_hub.drones.append(self)

    def set_hub(self, hub: Hub) -> None:
        self.hub = hub
