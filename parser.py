from Entities import DroneNetwork, HubType, Drone, Connection, Metadata_hub
def run_simulation_turn(dn: DroneNetwork, turn_count):
    # 1. Reset des liens
    for hub in dn.hubs.values():
        for conn in hub.connections:
            conn.reset_turn()

    for drone in dn.drones:
        # --- CAS A : LE DRONE EST EN TRANSIT (DÉJÀ EN VOL) ---
        if drone.waiting_time > 0:
            drone.waiting_time -= 1
            if drone.waiting_time == 0:
                # Arrivée au hub après l'attente
                connection = next(c for c in drone.hub.connections if
                                  (c.hub_from == drone.target_hub or c.hub_to == drone.target_hub))
                connection.drones_this_turn += 1
                drone.hub = drone.target_hub
                drone.hub.drones.append(drone)
                drone.target_hub = None
            continue

        # --- CAS B : LE DRONE EST SUR UN HUB ET DOIT DÉCIDER ---
        if drone.hub.hub_type == HubType.END_HUB:
            continue

        path = dn.get_shortest_path(drone)
        if len(path) < 2: continue

        next_hub = path[1]

        connection = next(c for c in drone.hub.connections if
                          (c.hub_from == drone.hub or c.hub_to == next_hub))

        if (connection.drones_this_turn < connection.metadata.get_attributs().get(
                'max_link_capacity') and \
                len(next_hub.drones) < next_hub.metadata.get_attributs().get(
            'max_drones') or next_hub.hub_type == HubType.END_HUB and \
                connection.drones_this_turn <
                connection.metadata.get_attributs().get('max_link_capacity')):

            dest_zone = next_hub.metadata.get_attributs()['zone']

            drone.hub.drones.remove(drone)
            connection.drones_this_turn += 1

            if dest_zone == Metadata_hub.ZoneType.restricted:
                drone.waiting_time = 1
                drone.target_hub = next_hub
            else:
                # Mouvement instantané (1 tour)
                drone.hub = next_hub
                drone.hub.drones.append(drone)

def execute_move(drone: Drone, target_hub, connection: Connection):
    # Retirer du hub actuel
    drone.hub.drones.remove(drone)

    # Mettre à jour le drone
    drone.hub = target_hub

    # Ajouter au nouveau hub et incrémenter la connexion
    target_hub.drones.append(drone)
    connection.drones_this_turn += 1
