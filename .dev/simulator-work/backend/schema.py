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
    if type(value) is not int or value < low or (high is not None and value > high):
        interval = f'entre {low} et {high}' if high is not None else f'au moins égal à {low}'
        raise InvalidConfiguration(f'{where} : entier {interval} requis.')


def selected_label_limit(nature, level):
    """Parcours par défaut des anciens scénarios sans capacités explicites."""
    return CATALOG['specific_states'][nature][level][0][0]


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise InvalidConfiguration('Profil invalide.')
    exact_keys(profile, ('level', 'nature', 'trait', 'pc', 'morale', 'labels', 'active', 'zombie', 'zombie_levels',
                         *[k for k in ('permanent', 'active_slots', 'banner_level', 'unlocked_evolutions', 'corpse_available', 'quest_heavy_cavalry') if k in profile]), 'Profil')
    if 'unlocked_evolutions' in profile:
        unlocked = profile['unlocked_evolutions']
        if (not isinstance(unlocked, list) or len(unlocked) > 7
                or any(type(i) is not int or i not in range(104, 111) for i in unlocked)
                or len(unlocked) != len(set(unlocked))):
            raise InvalidConfiguration('Déblocages invalides.')
    if 'corpse_available' in profile and type(profile['corpse_available']) is not bool:
        raise InvalidConfiguration('Disponibilité du cadavre booléenne requise.')
    if 'quest_heavy_cavalry' in profile and type(profile['quest_heavy_cavalry']) is not bool:
        raise InvalidConfiguration('Déblocage par quête booléen requis.')
    for key in ('level', 'pc', 'morale'):
        integer(profile[key], 0, CATALOG['limits'][key], key)
    if profile['nature'] not in CATALOG['natures'] or profile['trait'] not in CATALOG['traits']:
        raise InvalidConfiguration('Nature ou trait inconnu.')
    if type(profile['zombie']) is not bool:
        raise InvalidConfiguration('État zombie booléen requis.')
    integer(profile['zombie_levels'], 0, CATALOG['limits']['level'], 'Niveaux zombie')
    integer(profile.get('active_slots', 1), 1, 3, 'Emplacements actifs')
    integer(profile.get('banner_level', 0), 0, 2, 'Capacité d’étendard')
    labels = profile['labels']
    if not isinstance(labels, dict) or not set(labels) <= CATALOG['labels'].keys():
        raise InvalidConfiguration('Étiquettes inconnues.')
    for rank in labels.values():
        integer(rank, 1, CATALOG['label_rank_max'][profile['level']], 'Rang')
    for key in ('permanent', 'active'):
        names = profile.get(key, [])
        if (not isinstance(names, list) or not all(isinstance(n, str) for n in names)
                or len(names) != len(set(names)) or not set(names) <= labels.keys()):
            raise InvalidConfiguration('Sélection d’étiquettes inconnue ou dupliquée.')
    ordinary = [n for n in profile['active'] if not (profile['zombie'] and n == 'mort_vivant')]
    if profile['zombie_levels'] > profile['level'] or (not profile['zombie'] and profile['zombie_levels']):
        raise InvalidConfiguration('Niveaux après zombification incohérents.')
    possibles = CATALOG['specific_states'][profile['nature']][profile['level'] - profile['zombie_levels']]
    capacites = [profile.get('active_slots', 1), profile.get('banner_level', 0)]
    if 'active_slots' not in profile and 'banner_level' not in profile:
        capacites = possibles[0]
    if capacites not in possibles:
        raise InvalidConfiguration('Capacités spécifiques incompatibles avec le niveau et l’orientation.')
    if len(ordinary) > capacites[0]:
        raise InvalidConfiguration('Nombre d’étiquettes supérieur à la limite autorisée pour ce niveau et cette nature.')


def validate_generation(payload):
    if not isinstance(payload, dict):
        raise InvalidConfiguration('Génération : objet JSON requis.')
    exact_keys(payload, ('level', 'seed', *[k for k in ('nature', 'zombie', 'zombie_levels') if k in payload]), 'Génération')
    integer(payload['level'], 0, CATALOG['limits']['level'], 'Niveau')
    if payload['seed'] is not None:
        integer(payload['seed'], 0, 2**32 - 1, 'Graine')
    if 'nature' in payload and payload['nature'] not in CATALOG['natures']:
        raise InvalidConfiguration('Nature inconnue.')
    if type(payload.get('zombie', False)) is not bool:
        raise InvalidConfiguration('État zombie booléen requis.')
    integer(payload.get('zombie_levels', 0), 0, payload['level'], 'Niveaux après zombification')
    if payload.get('zombie_levels') and not payload.get('zombie'):
        raise InvalidConfiguration('Niveaux après zombification incohérents.')
    return payload


def validate_reward(payload):
    exact_keys(payload, ('profile', 'seed'), 'Récompense')
    validate_profile(payload['profile'])
    if payload['profile']['level'] >= CATALOG['limits']['level']:
        raise InvalidConfiguration('Niveau maximal atteint.')
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
            exact_keys(general, ('position', 'blocks', *[k for k in ('order', 'profile', 'qg', 'banner_block', 'qg_block') if k in general]), where)
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
            if general.get('banner_block') is not None:
                if general['banner_block'] not in CATALOG['blocks'] or 'profile' not in general:
                    raise InvalidConfiguration('Un bloc et un profil explicite sont nécessaires pour l’étendard.')
            if general.get('qg'):
                profile = general['profile']
                if (not isinstance(profile, dict) or profile.get('zombie') is not False
                        or profile.get('nature') not in ('stratege', 'hybride')):
                    raise InvalidConfiguration('Le quartier général est réservé aux stratèges.')
            if 'qg_block' in general and general['qg_block'] not in CATALOG['blocks']:
                raise InvalidConfiguration(f'{where} : bloc du QG inconnu.')
            if 'profile' in general:
                validate_profile(general['profile'])
            validate_blocks(general['blocks'], where, general.get('profile'))
        if sum(g.get('qg', False) for g in generals) > 1:
            raise InvalidConfiguration('Un seul QG par camp ; aucun départage automatique.')
    return payload
