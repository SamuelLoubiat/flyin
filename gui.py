import math
import tkinter as tk
from tkinter import TclError
from typing import List, Any

from DroneNetwork import DroneNetwork
from DroneNetwork import HubType
from entities import Hub, MetadataError
from parser import Parser


class DroneSimulationGUI:
    def __init__(self, root: tk.Tk, drone_network: DroneNetwork) -> None:
        self.root = root
        self.dn = drone_network
        self.root.title("Drone Simulator")

        self.padding = 100
        self.node_radius = 25
        self.history: List[Any] = []
        self.current_turn_index = 0

        self.precalculate_all_turns()
        self.print_result()

        self.main_frame = tk.Frame(root)
        self.main_frame.pack(expand=True, fill="both")

        self.h_scroll = tk.Scrollbar(self.main_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll = tk.Scrollbar(self.main_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")

        self.canvas = tk.Canvas(self.main_frame, width=1000, height=700,
                                bg="#2f3640",
                                xscrollcommand=self.h_scroll.set,
                                yscrollcommand=self.v_scroll.set)
        self.canvas.pack(side="left", expand=True, fill="both")

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.control_panel = tk.Frame(root)
        self.control_panel.pack(fill="x", pady=10)

        tk.Button(self.control_panel, text="Step ⏪", command=self.prev_step,
                  width=10).pack(side="left", padx=10)

        self.time_slider = tk.Scale(self.control_panel,
                                    from_=0,
                                    to=len(self.history) - 1,
                                    orient="horizontal",
                                    label="Navigation",
                                    command=self.slider_moved)
        self.time_slider.pack(side="left", fill="x", expand=True, padx=5)

        tk.Button(self.control_panel, text="Step ⏩", command=self.next_step,
                  width=10).pack(side="left", padx=10)

        self.root.bind("<Left>", lambda e: self.prev_step())
        self.root.bind("<Right>", lambda e: self.next_step())

        self._update_scaling_logic()
        self.load_state(0)
        self.draw_network()

    def precalculate_all_turns(self) -> None:

        self.save_state()

        max_turns = 1000
        turn_count = 0
        while any(
                d.hub.hub_type != HubType.END_HUB
                or d.waiting_time > 0 for d in self.dn.drones):
            self.dn.run_simulation_turn()
            self.save_state()
            turn_count += 1
            if turn_count >= max_turns:
                break

    def save_state(self) -> None:
        state = []
        for d in self.dn.drones:
            state.append({
                "id": d.id,
                "hub_name": d.hub.name if d.hub else None,
                "target_name": d.target_hub.name if d.target_hub else None,
                "waiting": d.waiting_time
            })
        self.history.append(state)

    def load_state(self, idx: int) -> None:
        state = self.history[idx]
        for h in self.dn.hubs.values():
            h.drone_hub.drones = []
        for d_data in state:
            drone = next(d for d in self.dn.drones if d.id == d_data["id"])
            new_hub = self.dn.hubs.get(d_data["hub_name"])
            if new_hub is not None:
                drone.hub = new_hub
            else:
                raise MetadataError("new hub is None")
            if drone.hub:
                drone.hub.drone_hub.drones.append(drone)
            drone.target_hub = self.dn.hubs.get(d_data["target_name"])
            drone.waiting_time = d_data["waiting"]

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

    def _update_scaling_logic(self) -> None:
        hubs = list(self.dn.hubs.values())
        if not hubs:
            return
        all_x, all_y = [h.x for h in hubs], [h.y for h in hubs]
        self.min_x, self.max_x = min(all_x), max(all_x)
        self.min_y, self.max_y = min(all_y), max(all_y)

        range_x = max(1, self.max_x - self.min_x)
        range_y = max(1, self.max_y - self.min_y)
        self.scale = 1800 / range_x

        total_w = range_x * self.scale + (2 * self.padding)
        total_h = range_y * self.scale + (2 * self.padding)
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))

    def get_coords(self, hub: Hub) -> tuple[float, float]:
        x = (hub.x - self.min_x) * self.scale + self.padding
        y = (hub.y - self.min_y) * self.scale + self.padding
        return x, y

    def slider_moved(self, val: Any) -> None:
        self.current_turn_index = int(val)
        self.load_state(self.current_turn_index)
        self.draw_network()

    def next_step(self) -> None:
        current = self.time_slider.get()
        if current < len(self.history) - 1:
            self.time_slider.set(current + 1)

    def prev_step(self) -> None:
        current = self.time_slider.get()
        if current > 0:
            self.time_slider.set(current - 1)

    def draw_network(self) -> None:
        self.canvas.delete("all")
        self._update_scaling_logic()

        drawn = set()
        for hub in self.dn.hubs.values():
            x1, y1 = self.get_coords(hub)
            for conn in hub.get_connections():
                other = conn.hub_to if conn.hub_from == hub else conn.hub_from
                pair = tuple(sorted((hub.name, other.name)))
                if pair not in drawn:
                    x2, y2 = self.get_coords(other)
                    self.canvas.create_line(x1, y1, x2, y2, fill="#7f8c8d",
                                            width=2)
                    drawn.add(pair)

        for hub in self.dn.hubs.values():
            x, y = self.get_coords(hub)
            color = hub.metadata.getattributes()['color']
            if color == 'rainbow':
                color = self.get_rainbow_color(self.current_turn_index)

            outline = "white"
            if hub.hub_type == HubType.START_HUB:
                outline = "#2ecc71"
            elif hub.hub_type == HubType.END_HUB:
                outline = "#e74c3c"

            try:
                self.canvas.create_oval(x - self.node_radius,
                                        y - self.node_radius,
                                        x + self.node_radius,
                                        y + self.node_radius,
                                        fill=color, outline=outline, width=3)
            except TclError:
                self.canvas.create_oval(x - self.node_radius,
                                        y - self.node_radius,
                                        x + self.node_radius,
                                        y + self.node_radius,
                                        fill='white', outline=outline, width=3)

            self.canvas.create_text(x, y - 40, text=hub.name, fill="white",
                                    font=("Arial", 10, "bold"))

            current_drones = sorted(hub.drone_hub.drones, key=lambda d: d.id)
            for i, drone in enumerate(current_drones):
                if drone.waiting_time == 0:
                    angle = i * (2 * math.pi / max(1, len(current_drones)))
                    dist = 15
                    dx, dy = x + math.cos(angle) * dist, y + math.sin(
                        angle) * dist
                    self.canvas.create_oval(dx - 5, dy - 5, dx + 5, dy + 5,
                                            fill="#3498db", outline="white")
                    self.canvas.create_text(dx, dy, text=str(drone.id),
                                            fill="white", font=("Arial", 6))

        for drone in self.dn.drones:
            if drone.waiting_time > 0 and drone.target_hub:
                x2, y2 = self.get_coords(drone.target_hub)
                if drone.hub:
                    x1, y1 = self.get_coords(drone.hub)
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2

                    self.canvas.create_oval(mx - 7, my - 7, mx + 7, my + 7,
                                            fill="#f1c40f", outline="black")
                    self.canvas.create_text(mx, my, text=str(drone.id),
                                            fill="black",
                                            font=("Arial", 7, "bold"))

    def get_rainbow_color(self, index: int) -> Any:
        colors = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF",
                  "#4B0082", "#8B00FF"]
        return colors[index % len(colors)]


if __name__ == "__main__":
    dn = DroneNetwork()
    ps = Parser()
    try:
        ps.parse_file(dn, "maps.txt")
        ps.validate(dn)
        dn.init_drone()

        root = tk.Tk()
        gui = DroneSimulationGUI(root, dn)
        root.mainloop()
    except Exception as e:
        print(f"Error: {e}")
