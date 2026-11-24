"""Construction synthétique à partir des API officielles, uniquement dans le worker."""
import random

from backend.schema import InvalidConfiguration


def engine_profile(profile):
    import progression
    if profile is None:
        return None
    p = profile
    fiche = progression.nouvelles_caracteristiques(random.Random(0))
    fiche.update(niveau=p['level'], nature=p['nature'],
                 trait_inne=p['trait'], points_commandement=p['pc'], moral=p['morale'],
                 etiquettes=dict(p['labels']),
                 emplacements_etiquettes_actives=p.get('active_slots', 1),
                 niveau_etendard=p.get('banner_level', 0),
                 etat_zombie=p['zombie'], niveaux_zombie=p['zombie_levels'])
    if p['zombie_levels'] > p['level'] or (not p['zombie'] and p['zombie_levels']):
        raise InvalidConfiguration('Niveaux après zombification incohérents.')
    try:
        progression.capacite_etiquettes_actives(fiche)
        # Reconstituer les états atteignables via les étapes du moteur : aucune
        # table de progression parallèle dans l'adaptateur.
        possibles = {(1, 0)}
        niveau_vivant = p['level'] - p['zombie_levels']
        for _ in range(min(4, niveau_vivant // 5)):
            suivants = set()
            for places, etendard in possibles:
                for branche in (0, 1):
                    candidat = dict(fiche, emplacements_etiquettes_actives=places, niveau_etendard=etendard)
                    progression.progression_specifique(candidat, TirageBranche(branche))
                    suivants.add((candidat['emplacements_etiquettes_actives'], candidat['niveau_etendard']))
            possibles = suivants
        if 'active_slots' not in p and 'banner_level' not in p:
            places, etendard = sorted(possibles)[0]
            fiche.update(emplacements_etiquettes_actives=places, niveau_etendard=etendard)
        elif (fiche['emplacements_etiquettes_actives'], fiche['niveau_etendard']) not in possibles:
            raise ValueError('Capacités spécifiques incompatibles avec le niveau et l’orientation.')
    except ValueError as exc:
        raise InvalidConfiguration(str(exc)) from exc
    # L'activation sera contrôlée par selection_etiquettes sur son vrai fichier.
    return fiche


class TirageBranche:
    """Explore les deux choix du moteur pour valider un scénario synthétique."""
    def __init__(self, branche):
        self.branche = branche

    def randint(self, minimum, maximum):
        return minimum if self.branche == 0 else maximum


def validate_army(general, fiche):
    import progression
    import unites
    composition = composition_requested(general)
    if unites.occupation(composition) > progression.capacite_maximale(fiche):
        raise InvalidConfiguration('Capacité dépassée : Messager = 5 places, Gros zombie = 10 places.')
    types = {t for bloc in composition.values() for t, n in bloc.items() if n}
    if fiche:
        for unit in types:
            if not progression.compatible(fiche, unites.definition(unit)['natures']):
                raise InvalidConfiguration(f'{unit} incompatible avec cette nature de général.')
    if sum(b.get('Trop_gros_zombie', 0) for b in composition.values()) > 1:
        raise InvalidConfiguration('Un seul Gros zombie par général.')
    if 'Trop_gros_zombie' in types and 'zombie' not in types:
        raise InvalidConfiguration('Le Gros zombie doit accompagner des Zombies ordinaires.')
    return composition


def composition_requested(general):
    result = {}
    for block, formation in general['blocks'].items():
        counts = {formation['unit']: formation['count']}
        for unit, count in (('messager_du_QG', formation.get('messengers', 0)),
                            ('Trop_gros_zombie', int(formation.get('shield', False)))):
            if count:
                counts[unit] = counts.get(unit, 0) + count
        result[block] = {t: n for t, n in counts.items() if n}
    return result


def generate(payload):
    from backend.engine_adapter import load_engine
    from backend.worker import protect
    from backend.schema import validate_generation
    import secrets
    protect()
    validate_generation(payload)
    load_engine()
    import progression
    seed = payload['seed'] if payload['seed'] is not None else secrets.randbits(32)
    rng = random.Random(seed)
    fiche = progression.nouvelles_caracteristiques(rng)
    for _ in range(payload['level']):
        fiche, _ = progression.monter_niveau(fiche, rng)
    return {'seed': seed, 'profile': {
        'level': fiche['niveau'], 'nature': fiche['nature'], 'trait': fiche['trait_inne'],
        'pc': fiche['points_commandement'], 'morale': fiche['moral'],
        'labels': fiche['etiquettes'],
        'active_slots': fiche['emplacements_etiquettes_actives'], 'banner_level': fiche['niveau_etendard'],
        'active': list(fiche['etiquettes'])[:progression.capacite_etiquettes_actives(fiche)],
        'zombie': False, 'zombie_levels': 0},
        'unlocked_evolutions': fiche['evolutions_acquises']}
