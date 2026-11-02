"""Préparation de scénarios synthétiques ; aucun calcul de combat local."""
import platform
import random
import secrets
import sys
import uuid
from fractions import Fraction

from backend.schema import CATALOG, LOCK, army_generals, validate
from backend.observer import CombatObserver
from backend.profiles import engine_profile, validate_army


def json_safe(value):
    if isinstance(value, Fraction):
        return int(value) if value.denominator == 1 else float(value)
    if isinstance(value, dict):
        return {str(k) if not isinstance(k, str) else k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    return value


def load_engine():
    sys.path.insert(0, "/engine")
    import config
    import etat
    import generaux
    import rapports
    import combats
    import catalogues
    if (config.ordre_blocs != CATALOG["blocks"] or config.max_unites_par_general != CATALOG["max_units"]
            or list(catalogues.UNITE_PAR_NOM) != CATALOG["units"]
            or json_safe({u['nom']: u for u in catalogues.UNITES.values()}) != CATALOG['unit_details']
            or catalogues.ETIQUETTES_COMBAT != CATALOG['labels']
            or config.emplacements != ["1", "2", "3", "4"]):
        raise RuntimeError("Catalogue incompatible avec le moteur.")
    return config, etat, generaux, rapports, combats


def prepare(payload):
    """Uniquement dans /game privé du worker ; aucun audit d'une vraie partie."""
    from backend.worker import protect
    protect()  # Refuse aussi un appel accidentel de l'adaptateur hors du worker.
    validate(payload)
    config, etat, generaux, rapports, combats = load_engine()
    seed = payload["seed"] if payload["seed"] is not None else secrets.randbits(32)
    config.game_path.mkdir(exist_ok=True)
    (config.game_path / ".systeme").mkdir(exist_ok=True)
    import progression
    import soldats
    import unites
    import bouclier_vivant
    # Flux indépendants : l'identité technique ne consomme pas de tirage de combat.
    identities = random.Random(seed ^ 0x1D3)
    uuid.uuid4 = lambda: uuid.UUID(int=identities.getrandbits(128), version=4)
    soldats.random = random.Random(seed ^ 0x501D)
    bouclier_vivant.random = random.Random(seed ^ 0xB0C1)
    progression.aleatoire_progression = random.Random(seed ^ 0x1234)
    profile = config.configuration_mode("classique")
    territory = config.game_path / "terrain1"
    generals = {}
    positions = {}
    # Les identités sont déterministes, distinctes des positions choisies.
    for camp, owner in (("A", "j1"), ("B", "j2")):
        generals[camp] = []
        for index, general in enumerate(army_generals(payload["armies"][camp]), 1):
            name = f"general{index}"
            path = territory / owner / str(general["position"]) / name
            path.mkdir(parents=True)
            # Fiche neutre, sans statistique supplémentaire ni tirage de création.
            (path / "fiche.txt").write_text(f"nom={name}\norientation=stratege\nstrategie=0\nforce=0\nexperience=0\n")
            generaux.creer_general(path, name)
            fiche = engine_profile(general.get('profile'))
            composition = validate_army(general, fiche)
            if fiche is not None:
                progression.enregistrer_creation(owner, name, fiche)
                progression.publier_fiche(path, fiche)
                (path / 'etiquettes_actives.txt').write_text('\n'.join(general['profile']['active']), encoding='utf-8')
                try:
                    progression.selection_etiquettes(fiche, path)
                except ValueError as exc:
                    from backend.schema import InvalidConfiguration
                    raise InvalidConfiguration(str(exc)) from exc
            if general.get('qg'):
                (path / 'QG.txt').touch()
            for block, counts in composition.items():
                for unit_type, count in counts.items():
                    for number in range(1, count + 1):
                        unit = path / block / f"{unites.definition(unit_type)['prefixe']}{number}"
                        unites.creer_officielle(unit, unit_type, {'simulateur': True})
                        if unit_type == 'messager_du_QG':
                            for item, mode in (('monocle', 0o700), ('sceau du roi', 0o070), ('enveloppe', 0o007)):
                                (unit / item).chmod(mode)
            generals[camp].append(path)
            positions[f"{owner}:{name}"] = territory.name
        etat.sauvegarder_compteur_general(owner, len(generals[camp]))
    etat.sauvegarder_positions_generaux(positions)
    etat.sauvegarder_generaux_fatigues(set())
    # Tirages du combat indépendants de la construction du scénario.
    combats.random = random.Random(seed)
    generaux.random = random.Random(seed)
    return (config, etat, generaux, rapports, combats), profile, territory, generals, seed


def snapshot(generaux, generals, payload):
    result = {}
    for camp, paths in generals.items():
        entries = []
        for path in paths:
            blocks = generaux.lire_composition_general(path)
            entries.append({"name": path.name, "position": int(path.parent.name),
                            "alive": path.exists(), "blocks": blocks,
                            "total": sum(sum(counts.values()) for counts in blocks.values())})
        if "blocks" in payload["armies"][camp]:
            result[camp] = {key: entries[0][key] for key in ("alive", "blocks", "total")}
        else:
            result[camp] = {"generals": entries, "total": sum(g["total"] for g in entries),
                            "surviving_generals": sum(g["alive"] for g in entries),
                            "destroyed_generals": sum(not g["alive"] for g in entries)}
    return result


def simulate(payload):
    modules, profile, territory, generals, seed = prepare(payload)
    config, etat, generaux, rapports, combats = modules
    before = snapshot(generaux, generals, payload)
    observer = CombatObserver(config, combats, generaux)
    mode, defender = payload.get("mode", "OFF/OFF"), payload.get("defender")
    import soldats
    import unites
    import commandement
    forces = generaux.lire_forces_territoire(territory, profile)
    present = [g for camp in forces.values() for g in camp.values() if g]
    qgs = [commandement.instantane_qg_territorial(g, present) for g in present if (g['chemin'] / 'QG.txt').exists()]
    initial_ids = set(soldats.charger())
    event = 'simulateur:terrain1'
    with observer, soldats.bataille_complete(event, profile):
        if mode == "OFF/DEF":
            combats.resoudre_combat_off_def(territory, "j1" if defender == "A" else "j2", profile)
        else:
            combats.resoudre_combat_v15(territory, profile)
        unites.terminer_territoire(territory, event, profile)
    health = soldier_summary(generals, soldats, initial_ids)
    healed = unites.soigner_victoire_territoriale(profile, territory, event)
    engagements = observer.engagements
    after = snapshot(generaux, generals, payload)
    control = generaux.controle_forces(generaux.lire_forces_territoire(territory, profile))
    outcome = {"j1": "A", "j2": "B", "neutre": "mutual_destruction", "conteste": "contested"}[control]
    observer.explain_absences(generals, control)
    # Explications des avantages obtenues par appel aux fonctions officielles.
    for engagement in engagements:
        for phase, details in (("choc", engagement["chocs"]), ("manoeuvre", engagement["manoeuvres"])):
            for detail in details:
                keys = ("1", "2") if phase == "choc" else ("attaquant", "defenseur")
                one, two = keys
                detail["values"] = {
                    key: {"base": combats.valeur_base_bloc({"type": detail[f"type_{key}"], "nombre": detail[f"initial_{key}"]}, detail[f"bloc_{key}"]),
                          "advantage": combats.multiplicateur(detail[f"type_{key}"], detail[f"type_{other}"])}
                    for key, other in ((one, two), (two, one))
                }
    return json_safe({"engine_commit": LOCK["commit"], "python_version": platform.python_version(), "seed": seed,
            "configuration": payload, "outcome": outcome, "before": before, "after": after,
            "losses": {camp: before[camp]["total"] - after[camp]["total"] for camp in before},
            "engagements": engagements,
            'calculations': observer.calculations,
            'morale_observations': observer.morale,
            "explanations": observer.explanations,
            'qg_initial': qgs, 'health_before_healing': health,
            'health': soldier_summary(generals, soldats, initial_ids), 'healed_by_shaman': healed,
            "journal": config.rapport_long_path.read_text(encoding="utf-8"),
            "conditions": {"mode": mode, "defender": defender, "fatigue": False,
                           "orders": [], 'reinforcements': False, 'retreats': False,
                           'scope': 'territorial_player_battle', 'value_floor_percent': 1}})


def soldier_summary(generals, soldats, initial_ids):
    registry = soldats.charger()
    result = {}
    for camp, paths in generals.items():
        result[camp] = []
        for path in paths:
            prefix = 'game/' + path.relative_to('/game').as_posix() + '/'
            records = [(key, value) for key, value in registry.items() if value['chemin'].startswith(prefix)]
            result[camp].append({'name': path.name, 'blocks': {
                block: {'wounded': sum(not v.get('detruit') and v['blessures'] > 0 for _, v in records if v['chemin'].startswith(prefix + block + '/')),
                        'wounds': sum(v['blessures'] for _, v in records if not v.get('detruit') and v['chemin'].startswith(prefix + block + '/')),
                        'created': sum(k not in initial_ids for k, v in records if v['chemin'].startswith(prefix + block + '/')),
                        'converted': sum('spore' in v.get('origine_officielle', {}) for _, v in records if v['chemin'].startswith(prefix + block + '/')),
                        'destroyed': sum(bool(v.get('detruit')) for _, v in records if v['chemin'].startswith(prefix + block + '/'))}
                for block in CATALOG['blocks']}})
    return result
