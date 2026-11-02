"""Contrat du prototype ; les capacités proviennent du moteur verrouillé."""
import json
from pathlib import Path

LOCK = json.loads((Path(__file__).with_name("engine.lock.json")).read_text(encoding="utf-8"))
CATALOG = LOCK["catalog"]


class InvalidConfiguration(ValueError):
    pass


def exact_keys(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise InvalidConfiguration(f"{where} : champs attendus {', '.join(keys)}.")


def army_generals(army):
    """Le contrat historique 1v1 reste accepté, sans ordre et en position 1."""
    if "blocks" in army:
        return [{"position": 1, "order": "", "blocks": army["blocks"]}]
    return army["generals"]


def integer(value, low, high, where):
    if type(value) is not int or not low <= value <= high:
        raise InvalidConfiguration(f'{where} : entier entre {low} et {high} requis.')


def validate_profile(profile):
    exact_keys(profile, ('level', 'nature', 'trait', 'pc', 'morale', 'labels', 'permanent', 'active', 'zombie', 'zombie_levels'), 'Profil')
    for key in ('level', 'pc', 'morale'):
        integer(profile[key], 0, CATALOG['limits'][key], key)
    if profile['nature'] not in CATALOG['natures'] or profile['trait'] not in CATALOG['traits']:
        raise InvalidConfiguration('Nature ou trait inconnu.')
    if type(profile['zombie']) is not bool:
        raise InvalidConfiguration('État zombie booléen requis.')
    integer(profile['zombie_levels'], 0, CATALOG['limits']['level'], 'Niveaux zombie')
    labels = profile['labels']
    if not isinstance(labels, dict) or not set(labels) <= CATALOG['labels'].keys():
        raise InvalidConfiguration('Étiquettes inconnues.')
    for rank in labels.values():
        integer(rank, 1, CATALOG['label_rank_max'][profile['level']], 'Rang')
    for key in ('permanent', 'active'):
        names = profile[key]
        if (not isinstance(names, list) or not all(isinstance(n, str) for n in names)
                or len(names) != len(set(names)) or not set(names) <= labels.keys()):
            raise InvalidConfiguration('Sélection d’étiquettes inconnue ou dupliquée.')


def validate_generation(payload):
    exact_keys(payload, ('level', 'seed'), 'Génération')
    integer(payload['level'], 0, CATALOG['limits']['level'], 'Niveau')
    if payload['seed'] is not None:
        integer(payload['seed'], 0, 2**32 - 1, 'Graine')
    return payload


def validate_blocks(blocks, where, profile=None):
    exact_keys(blocks, CATALOG["blocks"], where)
    total = 0
    for block, formation in blocks.items():
        if not isinstance(formation, dict):
            raise InvalidConfiguration('Bloc invalide.')
        exact_keys(formation, ('unit', 'count', *[k for k in ('messengers', 'shield') if k in formation]), f"{where}, {block}")
        unit, count = formation["unit"], formation["count"]
        if not isinstance(unit, str) or unit not in CATALOG["units"]:
            raise InvalidConfiguration(f"{where}, {block} : unité inconnue.")
        integer(count, 0, 120 if profile and profile['zombie'] else 20, where)
        integer(formation.get('messengers', 0), 0, 4, 'Messagers')
        if type(formation.get('shield', False)) is not bool:
            raise InvalidConfiguration('Bouclier booléen requis.')
        total += count * CATALOG['unit_details'][unit]['places'] + 5 * formation.get('messengers', 0) + 10 * formation.get('shield', False)
    if total < 1 or (profile is None and total > CATALOG['max_units']):
        raise InvalidConfiguration(f'{where} : capacité vide ou dépassée.')


def validate(payload):
    # Les requêtes historiques sans mode restent des combats OFF/OFF.
    explicit_mode = isinstance(payload, dict) and ("mode" in payload or "defender" in payload)
    keys = ("armies", "seed", "mode", "defender") if explicit_mode else ("armies", "seed")
    exact_keys(payload, keys, "Simulation")
    mode, defender = payload.get("mode", "OFF/OFF"), payload.get("defender")
    if mode not in ("OFF/OFF", "OFF/DEF"):
        raise InvalidConfiguration("Mode attendu : OFF/OFF ou OFF/DEF.")
    if (mode == "OFF/OFF" and defender is not None) or (mode == "OFF/DEF" and defender not in ("A", "B")):
        raise InvalidConfiguration("Défenseur attendu : A ou B en OFF/DEF, null en OFF/OFF.")
    seed = payload["seed"]
    if seed is not None and (type(seed) is not int or not 0 <= seed <= 2**32 - 1):
        raise InvalidConfiguration("La graine doit être un entier entre 0 et 4294967295, ou null.")
    exact_keys(payload["armies"], ("A", "B"), "Camps")
    for camp, army in payload["armies"].items():
        if isinstance(army, dict) and set(army) == {"blocks"}:
            validate_blocks(army["blocks"], f"Camp {camp}")
            continue
        exact_keys(army, ("generals",), f"Camp {camp}")
        generals = army["generals"]
        if not isinstance(generals, list) or not 1 <= len(generals) <= 4:
            raise InvalidConfiguration(f"Camp {camp} : de 1 à 4 généraux actifs requis.")
        occupied = set()
        for index, general in enumerate(generals, 1):
            where = f"Camp {camp}, général {index}"
            if not isinstance(general, dict):
                raise InvalidConfiguration('Général invalide.')
            exact_keys(general, ('position', 'blocks', *[k for k in ('order', 'profile', 'qg') if k in general]), where)
            position = general["position"]
            if type(position) is not int or position not in range(1, 5) or position in occupied:
                raise InvalidConfiguration(f"{where} : position unique entre 1 et 4 requise.")
            occupied.add(position)
            if general.get('order', '') != '':
                raise InvalidConfiguration('Les anciens ordres tactiques sont abandonnés.')
            if type(general.get('qg', False)) is not bool:
                raise InvalidConfiguration('Désignation QG booléenne requise.')
            if general.get('qg') and 'profile' not in general:
                raise InvalidConfiguration('Le QG doit avoir un profil explicite.')
            if 'profile' in general:
                validate_profile(general['profile'])
            validate_blocks(general['blocks'], where, general.get('profile'))
        if sum(g.get('qg', False) for g in generals) > 1:
            raise InvalidConfiguration('Un seul QG par camp ; aucun départage automatique.')
    return payload
