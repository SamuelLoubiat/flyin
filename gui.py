from tkinter import TclError

from Entities import DroneNetwork


import tkinter as tk
import math
from Entities import HubType


class DroneSimulationGUI:
    def __init__(self, root, drone_network):
        self.root = root
        self.dn = drone_network
        self.root.title("Drone Simulator - Full Control")

        # --- 1. CONFIGURATION VISUELLE ---
        self.padding = 100
        self.node_radius = 25
        self.history = []
        self.current_turn_index = 0

        # --- 2. PRÉ-CALCUL ---
        # On calcule toute la simulation avant d'afficher pour remplir la barre
        self.precalculate_all_turns()
        self.print_result()

        # --- 3. CONSTRUCTION DE L'INTERFACE (WIDGETS) ---
        # Frame principal pour le Canvas et les Scrollbars
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(expand=True, fill="both")

        # Scrollbars
        self.h_scroll = tk.Scrollbar(self.main_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll = tk.Scrollbar(self.main_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")

        # Canvas
        self.canvas = tk.Canvas(self.main_frame, width=1000, height=700,
                                bg="#2f3640",
                                xscrollcommand=self.h_scroll.set,
                                yscrollcommand=self.v_scroll.set)
        self.canvas.pack(side="left", expand=True, fill="both")

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        # Panneau de contrôle (Boutons + Slider)
        self.control_panel = tk.Frame(root)
        self.control_panel.pack(fill="x", pady=10)

        tk.Button(self.control_panel, text="Step ⏪", command=self.prev_step,
                  width=10).pack(side="left", padx=10)

        self.time_slider = tk.Scale(self.control_panel,
                                    from_=0,
                                    to=len(self.history) - 1,
                                    orient="horizontal",
                                    label="Navigation Temporelle",
                                    command=self.slider_moved)
        self.time_slider.pack(side="left", fill="x", expand=True, padx=5)

        tk.Button(self.control_panel, text="Step ⏩", command=self.next_step,
                  width=10).pack(side="left", padx=10)

        # --- 4. RACCOURCIS CLAVIER ---
        self.root.bind("<Left>", lambda e: self.prev_step())
        self.root.bind("<Right>", lambda e: self.next_step())

        # --- 5. INITIALISATION DU DESSIN ---
        self._update_scaling_logic()
        self.load_state(0)
        self.draw_network()

    def precalculate_all_turns(self):
        """Lance la simulation jusqu'à la fin pour enregistrer tous les états."""
        from parser import run_simulation_turn

        # État initial
        self.save_state()

        max_turns = 1000
        turn_count = 0
        # Tant qu'il reste des drones qui ne sont pas au hub de fin ou en transit
        while any(
                d.hub.hub_type != HubType.END_HUB or d.waiting_time > 0 for d in
                self.dn.drones):
            run_simulation_turn(self.dn, turn_count)
            self.save_state()
            turn_count += 1
            if turn_count >= max_turns: break

    def save_state(self):
        """Sauvegarde une copie de la position actuelle de tous les drones."""
        state = []
        for d in self.dn.drones:
            state.append({
                "id": d.id,
                "hub_name": d.hub.name if d.hub else None,
                "target_name": d.target_hub.name if d.target_hub else None,
                "waiting": d.waiting_time
            })
        self.history.append(state)

    def load_state(self, idx):
        """Restaure l'état du réseau au tour demandé."""
        state = self.history[idx]
        for h in self.dn.hubs.values():
            h.drones = []
        for d_data in state:
            drone = next(d for d in self.dn.drones if d.id == d_data["id"])
            drone.hub = self.dn.hubs.get(d_data["hub_name"])
            if drone.hub:
                drone.hub.drones.append(drone)
            drone.target_hub = self.dn.hubs.get(d_data["target_name"])
            drone.waiting_time = d_data["waiting"]

    def print_result(self):
        last_hub = {}
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


    def _update_scaling_logic(self):
        """Définit l'échelle pour que la carte soit grande et scrollable."""
        hubs = list(self.dn.hubs.values())
        if not hubs: return
        all_x, all_y = [h.x for h in hubs], [h.y for h in hubs]
        self.min_x, self.max_x = min(all_x), max(all_x)
        self.min_y, self.max_y = min(all_y), max(all_y)

        range_x = max(1, self.max_x - self.min_x)
        range_y = max(1, self.max_y - self.min_y)

        # On définit une échelle pour que la carte fasse environ 1800px
        self.scale = 1800 / range_x

        total_w = range_x * self.scale + (2 * self.padding)
        total_h = range_y * self.scale + (2 * self.padding)
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))

    def get_coords(self, hub):
        x = (hub.x - self.min_x) * self.scale + self.padding
        y = (hub.y - self.min_y) * self.scale + self.padding
        return x, y

    def slider_moved(self, val):
        self.current_turn_index = int(val)
        self.load_state(self.current_turn_index)
        self.draw_network()

    def next_step(self):
        current = self.time_slider.get()
        if current < len(self.history) - 1:
            self.time_slider.set(current + 1)

    def prev_step(self):
        current = self.time_slider.get()
        if current > 0:
            self.time_slider.set(current - 1)

    def draw_network(self):
        self.canvas.delete("all")
        self._update_scaling_logic()  # On s'assure que l'échelle est bonne

        # 1. DESSIN DES CONNEXIONS (LIGNES)
        drawn = set()
        for hub in self.dn.hubs.values():
            x1, y1 = self.get_coords(hub)
            for conn in hub.connections:
                other = conn.hub_to if conn.hub_from == hub else conn.hub_from
                pair = tuple(sorted((hub.name, other.name)))
                if pair not in drawn:
                    x2, y2 = self.get_coords(other)
                    self.canvas.create_line(x1, y1, x2, y2, fill="#7f8c8d",
                                            width=2)
                    drawn.add(pair)

        # 2. DESSIN DES HUBS
        for hub in self.dn.hubs.values():
            x, y = self.get_coords(hub)
            color = hub.metadata.get_attributs()['color']
            if color == 'rainbow':
                color = self.get_rainbow_color(self.current_turn_index)

            outline = "white"
            if hub.hub_type == HubType.START_HUB:
                outline = "#2ecc71"
            elif hub.hub_type == HubType.END_HUB:
                outline = "#e74c3c"

            try:
                self.canvas.create_oval(x - self.node_radius, y - self.node_radius,
                                    x + self.node_radius, y + self.node_radius,
                                    fill=color, outline=outline, width=3)
            except TclError:
                self.canvas.create_oval(x - self.node_radius,
                                        y - self.node_radius,
                                        x + self.node_radius,
                                        y + self.node_radius,
                                        fill='white', outline=outline, width=3)

            self.canvas.create_text(x, y - 40, text=hub.name, fill="white",
                                    font=("Arial", 10, "bold"))

            # 3. DRONES SUR LE HUB (Uniquement ceux qui sont VRAIMENT là)
            # On trie pour que l'affichage soit stable
            current_drones = sorted(hub.drones, key=lambda d: d.id)
            for i, drone in enumerate(current_drones):
                # On ne dessine ici que les drones qui ne sont pas en transit
                if drone.waiting_time == 0:
                    angle = i * (2 * math.pi / max(1, len(current_drones)))
                    dist = 15
                    dx, dy = x + math.cos(angle) * dist, y + math.sin(
                        angle) * dist
                    self.canvas.create_oval(dx - 5, dy - 5, dx + 5, dy + 5,
                                            fill="#3498db", outline="white")
                    self.canvas.create_text(dx, dy, text=str(drone.id),
                                            fill="white", font=("Arial", 6))

        # 4. DRONES EN VOL (ENTRE DEUX HUBS)
        for drone in self.dn.drones:
            # Un drone est en vol s'il a un target_hub ET un waiting_time > 0
            if drone.waiting_time > 0 and drone.target_hub:
                # On récupère les coordonnées de la cible
                x2, y2 = self.get_coords(drone.target_hub)

                # Pour le point de départ, on essaie de retrouver le hub d'où il vient
                # Si ton parser met drone.hub à None, il faut utiliser une autre astuce
                # Ici on suppose que drone.hub contient encore le hub de départ
                # (même s'il n'est plus dans hub.drones)
                if drone.hub:
                    x1, y1 = self.get_coords(drone.hub)

                    # Calcul de la progression (plus waiting_time est petit, plus on est proche)
                    # Si waiting_time = 1 sur un trajet de 2 tours, on est au milieu
                    # Pour simplifier, on affiche au milieu du segment :
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2

                    self.canvas.create_oval(mx - 7, my - 7, mx + 7, my + 7,
                                            fill="#f1c40f", outline="black")
                    self.canvas.create_text(mx, my, text=str(drone.id),
                                            fill="black",
                                            font=("Arial", 7, "bold"))

    def get_rainbow_color(self, index):
        """Retourne une couleur de l'arc-en-ciel basée sur un index."""
        colors = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF",
                  "#4B0082", "#8B00FF"]
        return colors[index % len(colors)]
# --- Lancement ---
if __name__ == "__main__":
    dn = DroneNetwork()
    # Assure-toi que le chemin du fichier est correct
    try:
        dn.parse_file("maps.txt")
        dn.validate()
        dn.init_drone()

        root = tk.Tk()
        gui = DroneSimulationGUI(root, dn)
        root.mainloop()
    except Exception as e:
        print(f"Erreur au démarrage : {e}")
        raise e