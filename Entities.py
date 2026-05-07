import re
from typing import Dict, List, Any

from entities import Connection, Drone, Hub, Metadata, MetadataError, HubType
from entities.Connection import MetadataConnection
from entities.Hub import MetadataHub


class DroneNetwork:
    ALLOWED_HUB_ATTRS = {'zone', 'color', 'max_drones'}
    ALLOWED_CONN_ATTRS = {'max_link_capacity'}
    regex_pattern = re.compile(r'''
        ^                       # Début de ligne
        (hub|start_hub|end_hub) # Type de hub
        :\s*                    # Séparateur : et espaces optionnels
        ([\w]+)                 # Nom (ID)
        \s+(-?\d+)              # Coordonnée X
        \s+(-?\d+)              # Coordonnée Y
        (?:\s+\[(.*)\])?        # Métadonnées optionnelles entre crochets
    ''', re.VERBOSE)

    def __init__(self) -> None:
        self.connexions_vues: set[Any] | None = None
        self.nb_drones: int = 0
        self.hubs: Dict[str, Hub] = {}
        self.drones: List[Drone] = []

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
            raise MetadataError(
                f"Le nom de hub '{hub.name}' est déjà utilisé.")

        for existing in self.hubs.values():
            if existing.x == hub.x and existing.y == hub.y:
                raise MetadataError(
                    f"Coords ({hub.x}, {hub.y}) déjà occupées par"
                    f" '{existing.name}'.")

        if hub.hub_type == HubType.START_HUB:
            if any(
                    h.hub_type == HubType.START_HUB for h in self.hubs.values()
            ):
                raise MetadataError("Un seul START_HUB est autorisé.")

        if hub.hub_type == HubType.END_HUB:
            if any(h.hub_type == HubType.END_HUB for h in self.hubs.values()):
                raise MetadataError("Un seul END_HUB est autorisé.")

        self.hubs[hub.name] = hub

    def add_connection(self, name_a: str, name_b: str,
                       meta: Metadata) -> None:
        if name_a not in self.hubs or name_b not in self.hubs:
            raise MetadataError(
                f"Lien impossible : {name_a} ou {name_b} inexistant.")

        hub_a = self.hubs[name_a]
        hub_b = self.hubs[name_b]
        conn = Connection(hub_a, hub_b, meta)
        hub_a.get_connections().append(conn)
        hub_b.get_connections().append(conn)

    def parse_file(self, file_path: str) -> None:
        self.connexions_vues = set()
        with (open(file_path, 'r') as f):
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if self.nb_drones is None \
                        and not line.startswith('nb_drones:'):
                    raise MetadataError(
                        f"Ligne {line_no}: 'nb_drones' doit être défini avant"
                        " toute autre donnée.")

                if line.startswith('nb_drones:'):
                    if self.nb_drones != 0:
                        raise MetadataError(
                            f"Ligne {line_no}: 'nb_drones' est déjà défini.")
                    try:
                        self.nb_drones = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        raise MetadataError(
                            f"Ligne {line_no}: nb_drones invalide.")
                    continue

                if any(line.startswith(t) for t in
                       ['hub:', 'start_hub:', 'end_hub:']):
                    h_match = self.regex_pattern.match(line)

                    if not h_match:
                        raise MetadataError(
                            f"Ligne {line_no}: Syntaxe Hub invalide.")

                    h_type_str, name, x, y, meta_str = h_match.groups()
                    raw_attrs = dict(re.findall(r'(\w+)=([\w#]+)',
                                                meta_str)) if meta_str else {}
                    extra_keys = set(raw_attrs.keys()) - self.ALLOWED_HUB_ATTRS
                    if extra_keys:
                        raise MetadataError(
                            f"Ligne {line_no}: Attribut(s) non autorisé(s)"
                            f" pour un Hub : {', '.join(extra_keys)}")
                    try:
                        meta_hub = MetadataHub(
                            zone=raw_attrs.get('zone', 'normal'),
                            color=raw_attrs.get('color', 'None'),
                            max_drones=int(raw_attrs.get('max_drones', 1))
                        )
                    except Exception as e:
                        raise MetadataError(f"Ligne {line_no}: {e}")

                    h_type_map = {
                        'start_hub': HubType.START_HUB,
                        'end_hub': HubType.END_HUB,
                        'hub': HubType.HUB
                    }

                    self.add_hub(
                        Hub(h_type_map[h_type_str], name, int(x), int(y),
                            meta_hub))
                    continue

                if line.startswith('connection:'):
                    c_match = re.match(
                        r'^connection:\s*(\w+)-(\w+)(?:\s+\[(.*)])?',
                        line)
                    if not c_match:
                        raise MetadataError(
                            f"Ligne {line_no}: Syntaxe Connexion invalide.")

                    name_from, name_to, meta_str = c_match.groups()
                    paire_triee = tuple(sorted((name_from, name_to)))

                    if paire_triee in self.connexions_vues:
                        raise MetadataError(
                            f"Ligne {line_no}: La connexion entre"
                            f" '{name_from}'"
                            f" et '{name_to}' est un doublon (déjà définie "
                            "dans un sens ou dans l'autre)."
                        )
                    self.connexions_vues.add(paire_triee)
                    raw_attrs = dict(re.findall(r'(\w+)=([\w#]+)',
                                                meta_str)) if meta_str else {}

                    extra_keys = \
                        set(raw_attrs.keys()) - self.ALLOWED_CONN_ATTRS
                    if extra_keys:
                        raise MetadataError(
                            f"Ligne {line_no}: Attribut(s) non autorisé(s)"
                            f" pour une Connexion : {', '.join(extra_keys)}"
                        )

                    meta_con = MetadataConnection(int(
                        raw_attrs.get('max_link_capacity', 1))
                    )

                    self.add_connection(name_from, name_to, meta_con)
                    continue

                raise MetadataError(
                    f"Ligne {line_no}: Format non reconnu -> '{line}'")

    def validate(self) -> None:
        starts = [h for h in self.hubs.values() if
                  h.hub_type == HubType.START_HUB]
        ends = [h for h in self.hubs.values() if h.hub_type == HubType.END_HUB]

        if len(starts) != 1:
            raise MetadataError(
                f"Erreur : {len(starts)} START_HUB trouvé(s) (1 requis).")
        if len(ends) != 1:
            raise MetadataError(
                f"Erreur : {len(ends)} END_HUB trouvé(s) (1 requis).")
        if self.nb_drones <= 0:
            raise MetadataError(
                "Erreur : Le nombre de drones doit être supérieur à 0.")

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
