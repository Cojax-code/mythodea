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
<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
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
=======
    fiche['evolutions_acquises'] = p.get('unlocked_evolutions', [])
    for name in p['permanent']:
        # Ancien contrat accepté, sans verrouiller le rang de cette connaissance.
        fiche['etiquettes'][name] = 1
        fiche['etiquettes_permanentes'].append(name)
    # Une connaissance de rang 1 peut venir de la roulette, sans quota scolaire
    # ni niveau 5 requis. Seules les améliorations suivent l'API de l'École.
    fiche['etiquettes'].update(dict.fromkeys(p['labels'], 1))
    try:
        for name, rank in p['labels'].items():
            for _ in range(rank - 1):
                fiche = progression.apprendre_etiquette(fiche, name)
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web
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
    profile = general.get('profile')
    if profile:
        options = profile_options(fiche)
        if not set(profile.get('unlocked_evolutions', [])) <= set(options['evolutions']):
            raise InvalidConfiguration('Déblocage incompatible avec la nature du général.')
        allowed = available_units(fiche, profile.get('corpse_available', False),
                                  profile.get('quest_heavy_cavalry', False))
        for block in composition.values():
            if not set(block) <= set(allowed):
                raise InvalidConfiguration('Unité incompatible avec le type du général ou les conditions du Gros zombie.')
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
    # Tirage conditionné sur la nature choisie, via la création officielle :
    # ni caractéristiques initiales ni probabilités de trait réinventées.
    if 'nature' in payload:
        while fiche['nature'] != payload['nature']:
            fiche = progression.nouvelles_caracteristiques(rng)
    history = []
    def record(level, reward):
        if isinstance(reward, tuple) and len(reward) == 2:
            kind, value = reward
            category = ('commandement' if kind == 'maitrise_commandement' else
                        'moral' if kind == 'force_caractere' else
                        'etiquette' if kind in ('etiquette', 'etiquette_zombie') else '')
            if category:
                history.append({'level': level, 'kind': category, 'value': str(value)})
        elif type(reward) is int and 104 <= reward <= 110:
            history.append({'level': level, 'kind': 'unite', 'value': str(reward)})

    zombie_levels = payload.get('zombie_levels', 0)
    for level in range(1, payload['level'] - zombie_levels + 1):
        fiche, reward = progression.monter_niveau(fiche, rng)
        record(level, reward)
    if payload.get('zombie'):
        fiche.update(etat_zombie=True, niveaux_zombie=0)
        for level in range(payload['level'] - zombie_levels + 1, payload['level'] + 1):
            fiche, reward = progression.monter_niveau(fiche, rng)
            record(level, reward)
    from pathlib import Path
    from backend.schema import LOCK
    # Le répertoire privé est vide : le moteur choisit sa sélection par défaut.
    fiche = progression.selection_etiquettes(fiche, Path('/game'))
    return {'seed': seed, 'engine_commit': LOCK['commit'],
        'engine_revision': LOCK.get('revision', LOCK['commit']), 'profile': {
        'level': fiche['niveau'], 'nature': fiche['nature'], 'trait': fiche['trait_inne'],
        'pc': fiche['points_commandement'], 'morale': fiche['moral'],
<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
        'labels': fiche['etiquettes'],
        'active_slots': fiche['emplacements_etiquettes_actives'], 'banner_level': fiche['niveau_etendard'],
        'active': list(fiche['etiquettes'])[:progression.capacite_etiquettes_actives(fiche)],
        'zombie': False, 'zombie_levels': 0},
        'unlocked_evolutions': fiche['evolutions_acquises']}
=======
        'labels': fiche['etiquettes'], 'permanent': [],
        'active': fiche['etiquettes_actives'], 'zombie': bool(fiche.get('etat_zombie')),
        'zombie_levels': fiche.get('niveaux_zombie', 0)},
        'unlocked_evolutions': fiche['evolutions_acquises'],
        'rewards': history}


def profile_options(fiche):
    """Données de formulaire calculées par les API du moteur verrouillé."""
    import progression
    import catalogues
    eligible = progression.evolutions_eligibles(dict(fiche, evolutions_acquises=[]))
    evolutions = {i: catalogues.UNITES[e['cible']]['nom']
                  for i, e in eligible.items() if e['categorie'] == 'unite'}
    return dict(evolutions=evolutions,
                compatible_units=[u['nom'] for u in catalogues.UNITES.values()
                                  if progression.compatible(fiche, u['natures'])])


def available_units(fiche, corpse_available=False, quest_heavy_cavalry=False):
    import unites
    import catalogues
    options = profile_options(fiche)
    if fiche.get('etat_zombie'):
        # Le rituel exige un zombie et un cadavre officiel non consommé.
        # La campagne et ses preuves Linux ne sont pas simulées.
        return ['zombie'] + (['Trop_gros_zombie'] if corpse_available else [])
    unlocked = set(fiche.get('evolutions_acquises', []))
    required = {catalogues.UNITES[e['cible']]['nom']: i
                for i, e in catalogues.EVOLUTIONS.items()
                if e['disponible'] and e['categorie'] == 'unite'}
    return [name for name in options['compatible_units']
            if not unites.etiquette(name, 'mort_vivant') and
            (name not in required or required[name] in unlocked or
             name == 'cavalerie_lourde' and quest_heavy_cavalry)]


def configuration_options():
    from backend.engine_adapter import load_engine
    load_engine()
    import progression
    from backend.schema import CATALOG
    result = {}
    for nature in CATALOG['natures']:
        fiche = progression.nouvelles_caracteristiques(random.Random(0))
        fiche.update(nature=nature, evolutions_acquises=[])
        options = profile_options(fiche)
        from backend.schema import selected_label_limit
        roulette = progression.evolutions_eligibles(fiche, apprentissage=False)
        result[nature] = dict(options, roulette_evolutions={
            i: options['evolutions'][i] for i, e in roulette.items() if e['categorie'] == 'unite'},
            reward_weights=progression.RECOMPENSES['hybride' if nature.endswith('_hybride') else nature],
            selected_label_limits=[
            selected_label_limit(nature, level) for level in range(CATALOG['limits']['level'] + 1)])
    fiche['etat_zombie'] = True
    capacities = []
    for level in range(CATALOG['limits']['level'] + 1):
        fiche['niveaux_zombie'] = level
        capacities.append(progression.capacite_maximale(fiche))
    return dict(natures=result, zombie_capacities=capacities,
                normal_capacity=progression.capacite_maximale(None))


def natural(payload):
    """Aucune roulette : mêmes gains naturels que monter_niveau, depuis zéro."""
    from backend.engine_adapter import load_engine
    from backend.schema import validate_generation, LOCK
    import secrets
    validate_generation(payload)
    load_engine()
    import progression
    seed = payload['seed'] if payload['seed'] is not None else secrets.randbits(32)
    rng = random.Random(seed)
    fiche = progression.nouvelles_caracteristiques(random.Random(0))
    fiche['nature'] = payload.get('nature', fiche['nature'])
    for level in range(1, payload['level'] - payload.get('zombie_levels', 0) + 1):
        fiche['niveau'] = level
        fiche = progression.appliquer_gains_naturels(fiche, rng)
    return dict(pc=fiche['points_commandement'], morale=fiche['moral'], seed=seed,
                engine_commit=LOCK['commit'])


def reward(payload):
    """Un seul niveau tiré par la roulette officielle sur les acquis précédents."""
    from backend.engine_adapter import load_engine
    from backend.schema import validate_reward, LOCK
    import secrets
    validate_reward(payload)
    load_engine()
    import progression
    seed = payload['seed'] if payload['seed'] is not None else secrets.randbits(32)
    fiche = engine_profile(payload['profile'])
    _, result = progression.monter_niveau(fiche, random.Random(seed))
    if isinstance(result, tuple):
        kind, value = result
        kind = {'maitrise_commandement': 'commandement', 'force_caractere': 'moral',
                'etiquette_zombie': 'etiquette'}.get(kind, kind)
    elif isinstance(result, int):
        kind, value = 'unite', result
    else:
        kind, value = '', ''
    return dict(reward=dict(kind=kind, value=str(value)), seed=seed, engine_commit=LOCK['commit'])
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web
