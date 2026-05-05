import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List


class MetadataError(Exception):
    """Exception personnalisée pour les erreurs de parsing ou de structure."""
    pass


class Metadata(ABC):
    @abstractmethod
    def get_attributs(self) -> dict:
        pass


class Metadata_hub(Metadata):
    class ZoneType(Enum):
        normal = 1
        blocked = 3
        restricted = 2
        priority = 0

    def __init__(self, zone: str = 'normal', color: str = 'None',
                 max_drones: int = 1) -> None:
        try:
            # Conversion du string en Enum
            meta_zone = Metadata_hub.ZoneType[zone.lower()]
        except KeyError:
            raise MetadataError(f"'{zone}' is not a valid zone type")

        if max_drones <= 0:
            raise MetadataError("max_drones must be greater than 0")

        self.attributs = {
            'zone': meta_zone,
            'color': color,
            'max_drones': max_drones
        }

    def get_attributs(self) -> dict:
        return self.attributs


class Metadata_connection(Metadata):
    def __init__(self, max_link_capacity: int = 1) -> None:
        if max_link_capacity <= 0:
            raise MetadataError("max_link_capacity must be greater than 0")
        self.attributs = {'max_link_capacity': max_link_capacity}

    def get_attributs(self) -> dict:
        return self.attributs


class HubType(Enum):
    START_HUB = 1
    HUB = 2
    END_HUB = 3


class Hub:
    def __init__(self, hub_type: HubType, name: str, x: int, y: int,
                 metadata: Metadata_hub) -> None:
        self.hub_type = hub_type
        self.name = name
        self.x = x
        self.y = y
        self.metadata = metadata
        self.connections: List['Connection'] = []
        self.drones: List['Drone'] = []

    def add_connection(self, connection: 'Connection'):
        self.connections.append(connection)

    def can_receive_drone(self) -> bool:
        max_allowed = self.metadata.get_attributs().get('max_drones')
        return len(self.drones) < max_allowed


class Connection:
    """Représente une liaison entre deux Hubs pour l'historique ou le debug."""

    def __init__(self, hub_from: Hub, hub_to: Hub,
                 metadata: Metadata_connection) -> None:
        self.hub_from = hub_from
        self.hub_to = hub_to
        self.metadata = metadata
        self.drones_this_turn = 0

    def reset_turn(self):
        self.drones_this_turn = 0

    def can_pass(self) -> bool:
        max_capa = self.metadata.get_attributs().get('max_link_capacity', 1)
        return self.drones_this_turn < max_capa


class Drone:

    def __init__(self, id: int, hub: Hub):
        self.id = id
        self.hub = hub
        self.waiting_time = 0
        self.target_hub = None
        hub.drones.append(self)

    def set_hub(self, hub: Hub):
        self.hub = hub


class DroneNetwork:
    ALLOWED_HUB_ATTRS = {'zone', 'color', 'max_drones'}
    ALLOWED_CONN_ATTRS = {'max_link_capacity'}
    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.hubs: Dict[str, Hub] = {}
        self.drones = []

    def init_drone(self):
        start_hub = next(
            (h for h in self.hubs.values() if h.hub_type == HubType.START_HUB),
            None)
        for i in range(1, self.nb_drones + 1):
            self.drones.append(Drone(i, start_hub))

    def add_hub(self, hub: Hub) -> None:
        """Ajoute un hub au réseau avec vérifications de validité."""
        # 1. Vérification du nom unique
        if hub.name in self.hubs:
            raise MetadataError(f"Le nom de hub '{hub.name}' est déjà utilisé.")

        # 2. Vérification des coordonnées uniques
        for existing in self.hubs.values():
            if existing.x == hub.x and existing.y == hub.y:
                raise MetadataError(
                    f"Coords ({hub.x}, {hub.y}) déjà occupées par '{existing.name}'."
                )

        # 3. Vérification de l'unicité du START/END
        if hub.hub_type == HubType.START_HUB:
            if any(h.hub_type == HubType.START_HUB for h in self.hubs.values()):
                raise MetadataError("Un seul START_HUB est autorisé.")

        if hub.hub_type == HubType.END_HUB:
            if any(h.hub_type == HubType.END_HUB for h in self.hubs.values()):
                raise MetadataError("Un seul END_HUB est autorisé.")

        self.hubs[hub.name] = hub

    def add_connection(self, name_a: str, name_b: str,
                       meta: Metadata_connection) -> None:
        """Établit un lien bidirectionnel entre deux hubs (Graphe)."""
        if name_a not in self.hubs or name_b not in self.hubs:
            raise MetadataError(
                f"Lien impossible : {name_a} ou {name_b} inexistant.")

        hub_a = self.hubs[name_a]
        hub_b = self.hubs[name_b]
        conn = Connection(hub_a, hub_b, meta)
        hub_a.add_connection(conn)
        hub_b.add_connection(conn)

    def parse_file(self, file_path: str) -> None:
        self.connexions_vues = set()
        """Parse le fichier d'entrée et construit le réseau d'objets."""
        self.nb_drones = None
        with open(file_path, 'r') as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if self.nb_drones is None and not line.startswith('nb_drones:'):
                    raise MetadataError(
                        f"Ligne {line_no}: 'nb_drones' doit être défini avant toute autre donnée."
                    )

                # Nombre de drones
                if line.startswith('nb_drones:'):
                    if self.nb_drones is not None:
                        raise MetadataError(
                            f"Ligne {line_no}: 'nb_drones' est déjà défini.")
                    try:
                        self.nb_drones = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        raise MetadataError(
                            f"Ligne {line_no}: nb_drones invalide.")
                    continue

                # Définition de Hub
                if any(line.startswith(t) for t in
                       ['hub:', 'start_hub:', 'end_hub:']):
                    h_match = re.match(
                        r'^(hub|start_hub|end_hub):\s*([\w]+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.*)\])?',
                        line)

                    if not h_match:
                        raise MetadataError(
                            f"Ligne {line_no}: Syntaxe Hub invalide.")

                    h_type_str, name, x, y, meta_str = h_match.groups()

                    # Extraction metadata
                    raw_attrs = dict(re.findall(r'(\w+)=([\w#]+)',
                                                meta_str)) if meta_str else {}
                    extra_keys = set(raw_attrs.keys()) - self.ALLOWED_HUB_ATTRS
                    if extra_keys:
                        raise MetadataError(
                            f"Ligne {line_no}: Attribut(s) non autorisé(s) pour un Hub : {', '.join(extra_keys)}"
                        )
                    try:
                        meta_obj = Metadata_hub(
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
                            meta_obj))
                    continue

                # Définition de Connection
                if line.startswith('connection:'):
                    c_match = re.match(
                        r'^connection:\s*([\w]+)-([\w]+)(?:\s+\[(.*)\])?', line)
                    if not c_match:
                        raise MetadataError(
                            f"Ligne {line_no}: Syntaxe Connexion invalide.")

                    name_from, name_to, meta_str = c_match.groups()
                    paire_triee = tuple(sorted((name_from, name_to)))

                    if paire_triee in self.connexions_vues:
                        raise MetadataError(
                            f"Ligne {line_no}: La connexion entre '{name_from}' et '{name_to}' est un doublon (déjà définie dans un sens ou dans l'autre)."
                        )

                    # On l'ajoute au set pour les prochaines lignes
                    self.connexions_vues.add(paire_triee)
                    raw_attrs = dict(re.findall(r'(\w+)=([\w#]+)',
                                                meta_str)) if meta_str else {}

                    extra_keys = set(raw_attrs.keys()) - self.ALLOWED_CONN_ATTRS
                    if extra_keys:
                        raise MetadataError(
                            f"Ligne {line_no}: Attribut(s) non autorisé(s) pour une Connexion : {', '.join(extra_keys)}"
                        )

                    meta_obj = Metadata_connection(
                        max_link_capacity=int(
                            raw_attrs.get('max_link_capacity', 1))
                    )

                    self.add_connection(name_from, name_to, meta_obj)
                    continue

                raise MetadataError(
                    f"Ligne {line_no}: Format non reconnu -> '{line}'")

    def validate(self) -> None:
        """Vérifie que le réseau est prêt pour la simulation."""
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
        """
        Calcule le chemin qui prend le MOINS DE TOURS possible.
        Prend en compte les zones restricted et l'encombrement des hubs.
        """
        start_hub = drone.hub
        end_hub = next(
            (h for h in self.hubs.values() if h.hub_type == HubType.END_HUB),
            None)

        if not start_hub or not end_hub:
            return []

        distances = {name: float('inf') for name in self.hubs}
        distances[start_hub.name] = 0
        previous_hubs = {name: None for name in self.hubs}
        unvisited = list(self.hubs.keys())

        while unvisited:
            # On choisit le hub avec la distance (en tours) la plus faible
            curr_name = min(unvisited, key=lambda n: distances[n])
            if distances[curr_name] == float('inf'): break

            curr_hub = self.hubs[curr_name]
            unvisited.remove(curr_name)
            if curr_hub == end_hub: break

            for conn in curr_hub.connections:
                neighbor = conn.hub_to if conn.hub_from == curr_hub else conn.hub_from
                if neighbor.name not in unvisited: continue

                # --- CALCUL DU COÛT EN TOURS ---
                # 1. Coût de base de la zone
                z_type = neighbor.metadata.get_attributs()['zone']
                if z_type == Metadata_hub.ZoneType.restricted:
                    cost = 2.0  # Traverser une zone restricted prend 2 tours
                elif z_type == Metadata_hub.ZoneType.blocked:
                    cost = 999.0
                elif z_type == Metadata_hub.ZoneType.priority:
                    cost = 0.5
                else:
                    cost = 1.0  # Zone normale = 1 tourzz

                cost += len(neighbor.drones)

                if distances[curr_name] + cost < distances[neighbor.name]:
                    distances[neighbor.name] = distances[curr_name] + cost
                    previous_hubs[neighbor.name] = curr_hub

        # Reconstruction
        path = []
        curr = end_hub
        if distances[end_hub.name] == float('inf'): return []
        while curr:
            path.append(curr)
            curr = previous_hubs[curr.name]
        return path[::-1]

    def display_state(self, turn: int):
        print(f"\n{'=' * 10} TOUR {turn} {'=' * 10}")
        for hub in self.hubs.values():
            # Déterminer l'icône selon le type
            icon = "🏠" if hub.hub_type == HubType.HUB else "🚀" if hub.hub_type == HubType.START_HUB else "🏁"

            # Liste des IDs des drones présents
            drone_ids = [d.id for d in hub.drones]

            # Affichage de la ligne du Hub
            capa = hub.metadata.get_attributs().get('max_drones', 1)
            zone = hub.metadata.get_attributs().get('zone').name

            print(
                f"{icon} {hub.name:<10} [{zone:^10}] : {len(drone_ids)}/{capa} drones {drone_ids}")

        # Optionnel : Afficher les drones en transit (si tu as implémenté le waiting_time)
        transit = [d for d in self.drones if d.waiting_time > 0]
        if transit:
            print(
                f"✈️  EN TRANSIT : {[(d.id, d.target_hub.name) for d in transit]}")
        print("-" * 30)