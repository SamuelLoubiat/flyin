import re

from DroneNetwork import DroneNetwork, HubNameError
from entities import Hub, HubType, MetadataError
from entities.Connection import MetadataConnection
from entities.Hub import MetadataHub


class ParserError(Exception):
    pass


class Parser:
    ALLOWED_HUB_ATTRS = {'zone', 'color', 'max_drones'}
    ALLOWED_CONN_ATTRS = {'max_link_capacity'}
    regex_hub = re.compile(r'''^(hub|start_hub|end_hub)
            :\s*([\w]+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.*)\])?''', re.VERBOSE)
    regex_connection = re.compile(
        r'''^connection:\s*([a-zA-Z0-9_]+)-([a-zA-Z0-9_]+)
        (?:\s+\[(.*)])?$''', re.VERBOSE)

    def __init__(self) -> None:
        self.connexions: None | set = None

    def parse_file(self, dn: DroneNetwork, file_path: str) -> None:
        self.connexions = set()
        with (open(file_path, 'r') as f):
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if dn.nb_drones is None \
                        and not line.startswith('nb_drones:'):
                    raise ParserError(
                        f"Line {line_no}: 'nb_drones' must be the first"
                        " data.")

                if line.startswith('nb_drones:'):
                    if dn.nb_drones != 0:
                        raise ParserError(
                            f"Line {line_no}: 'nb_drones' is already define.")
                    try:
                        dn.nb_drones = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        raise ParserError(
                            f"Line {line_no}: nb_drones is not valid.")
                    continue

                if any(line.startswith(t) for t in
                       ['hub:', 'start_hub:', 'end_hub:']):
                    h_match = self.regex_hub.match(line)

                    if not h_match:
                        raise MetadataError(
                            f"Line {line_no}: invalid Hub syntax.")

                    h_type_str, name, x, y, meta_str = h_match.groups()
                    raw_attrs = dict(re.findall(r'(\w+)=([\w#]+)',
                                                meta_str)) if meta_str else {}
                    extra_keys = set(raw_attrs.keys()) - self.ALLOWED_HUB_ATTRS
                    if extra_keys:
                        raise MetadataError(
                            f"Line {line_no}: Attribute not authorized"
                            f" for one Hub : {', '.join(extra_keys)}")
                    try:
                        meta_hub = MetadataHub(
                            zone=raw_attrs.get('zone', 'normal'),
                            color=raw_attrs.get('color', 'None'),
                            max_drones=int(raw_attrs.get('max_drones', 1))
                        )
                    except Exception as e:
                        raise MetadataError(f"Line {line_no}: {e}")

                    h_type_map = {
                        'start_hub': HubType.START_HUB,
                        'end_hub': HubType.END_HUB,
                        'hub': HubType.HUB
                    }

                    dn.add_hub(
                        Hub(h_type_map[h_type_str], name, int(x), int(y),
                            meta_hub))
                    continue

                if line.startswith('connection:'):
                    c_match = self.regex_connection.match(line)
                    if not c_match:
                        raise ParserError(
                            f"Error: Line {line_no}:"
                            " Invalid connection syntax.")

                    name_from, name_to, meta_str = c_match.groups()
                    paire_triee = tuple(sorted((name_from, name_to)))

                    if paire_triee in self.connexions:
                        raise ParserError(
                            f"Line {line_no}: the connexion between"
                            f" '{name_from}'"
                            f" and '{name_to}' is already define")
                    self.connexions.add(paire_triee)
                    raw_attrs = dict(re.findall(r'(\w+)=([\w#]+)',
                                                meta_str)) if meta_str else {}

                    extra_keys = \
                        set(raw_attrs.keys()) - self.ALLOWED_CONN_ATTRS
                    if extra_keys:
                        raise MetadataError(
                            f"Line {line_no}: bad attribute"
                            f" {', '.join(extra_keys)}"
                        )

                    meta_con = MetadataConnection(int(
                        raw_attrs.get('max_link_capacity', 1))
                    )
                    try:
                        dn.add_connection(name_from, name_to, meta_con)
                    except HubNameError as e:
                        raise ParserError(f"Error: Line {line_no}: {e}")
                    continue

                raise ParserError(
                    f"Error: Line {line_no}: unknown format -> '{line}'")

    def validate(self, dn: DroneNetwork) -> None:
        starts = [h for h in dn.hubs.values() if
                  h.hub_type == HubType.START_HUB]
        ends = [h for h in dn.hubs.values() if h.hub_type == HubType.END_HUB]

        if len(starts) != 1:
            raise MetadataError(
                f"Erreur : {len(starts)} START_HUB trouvé(s) (1 requis).")
        if len(ends) != 1:
            raise MetadataError(
                f"Erreur : {len(ends)} END_HUB trouvé(s) (1 requis).")
        if dn.nb_drones <= 0:
            raise MetadataError(
                "Erreur : Le nombre de drones doit être supérieur à 0.")
