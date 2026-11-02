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
                 orientation_principale=p['nature'].removesuffix('_hybride'),
                 trait_inne=p['trait'], points_commandement=p['pc'], moral=p['morale'],
                 etiquettes={}, etiquettes_permanentes=[],
                 etat_zombie=p['zombie'], niveaux_zombie=p['zombie_levels'])
    if p['zombie_levels'] > p['level'] or (not p['zombie'] and p['zombie_levels']):
        raise InvalidConfiguration('Niveaux après zombification incohérents.')
    orientation = progression.orientation_principale(fiche)
    max_permanent = (1 + min(2, p['level'] // 5) if orientation == 'stratege'
                     else int(p['level'] >= 5))
    if len(p['permanent']) > max_permanent:
        raise InvalidConfiguration('Trop d’étiquettes permanentes pour ce niveau.')
    for name in p['permanent']:
        if p['labels'].get(name) != 1:
            raise InvalidConfiguration('Une étiquette permanente conserve son rang 1.')
        fiche['etiquettes'][name] = 1
        fiche['etiquettes_permanentes'].append(name)
    try:
        for name, rank in p['labels'].items():
            if name in p['permanent']:
                continue
            if p['zombie'] and name == 'mort_vivant':
                continue
            for _ in range(rank):
                fiche = progression.apprendre_etiquette(fiche, name)
        if p['zombie'] and 'mort_vivant' in p['labels']:
            fiche['etiquettes']['mort_vivant'] = 1
            for _ in range(p['labels']['mort_vivant'] - 1):
                fiche = progression.apprendre_etiquette(fiche, 'mort_vivant')
    except ValueError as exc:
        raise InvalidConfiguration(str(exc)) from exc
    # L'activation sera contrôlée par selection_etiquettes sur son vrai fichier.
    return fiche


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
        'labels': fiche['etiquettes'], 'permanent': fiche['etiquettes_permanentes'],
        'active': list(fiche['etiquettes']), 'zombie': False, 'zombie_levels': 0},
        'unlocked_evolutions': fiche['evolutions_acquises']}
