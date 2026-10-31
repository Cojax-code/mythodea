"""Caractéristiques, jauges indépendantes et récompenses officielles des généraux."""
from copy import deepcopy
import json
import random

import catalogues


TRAITS = {
    'stratege': {'charismatique': 50, 'leader': 35, 'inventeur': 15},
    'instinctif': {'charismatique': 50, 'leader': 15, 'inventeur': 35},
}
RECOMPENSES = {
    'stratege': {
        'charismatique': {'commandement': 60, 'unite': 10},
        'leader': {'commandement': 20, 'unite': 10},
        'inventeur': {'commandement': 20, 'unite': 60},
    },
    'instinctif': {
        'charismatique': {'moral': 60, 'unite': 25},
        'leader': {'moral': 20, 'unite': 20},
        'inventeur': {'moral': 20, 'unite': 70},
    },
}

NATURES = {'stratege': 45, 'instinctif': 45,
           'stratege_hybride': 5, 'instinctif_hybride': 5}
SEUILS = {'combat': 2, 'formation': 3}
# Les récompenses ne modifient pas la suite des tirages des combats.
aleatoire_progression = random.Random()


def orientation_principale(fiche):
    # Dérivée de la nature officielle immuable, jamais d'un fichier joueur.
    return fiche['nature'].removesuffix('_hybride')


def compatible(fiche, natures, apprentissage=True):
    return (natures is None or orientation_principale(fiche) in natures or
            (apprentissage and fiche['nature'] in ('stratege_hybride', 'instinctif_hybride')))


def tirer_pondere(poids, aleatoire=None):
    """Tirage entier exact ; les catégories exclues ne conservent aucun poids."""
    aleatoire = random if aleatoire is None else aleatoire
    if not poids or any(type(p) is not int or p <= 0 for p in poids.values()):
        raise ValueError('Au moins un poids entier strictement positif est requis.')
    tirage = aleatoire.randint(1, sum(poids.values()))
    for valeur, poids_valeur in poids.items():
        tirage -= poids_valeur
        if tirage <= 0:
            return valeur


def gain_commandement(niveau, aleatoire=None):
    if type(niveau) is not int or niveau < 0:
        raise ValueError('Niveau entier positif ou nul requis.')
    aleatoire = random if aleatoire is None else aleatoire
    tranche = 10 * (niveau // 5 + 1)
    return tranche + aleatoire.randint(1, tranche)


def gain_pc_naturel(aleatoire):
    return aleatoire.randint(2, 4)


def gain_moral_naturel(niveau):
    # +1 aux niveaux pairs (2, 4, 6...), sans tirage supplémentaire.
    return 1 if niveau % 2 == 0 else 0


def recompense_statistique(orientation, aleatoire):
    if orientation == 'stratege':
        return 'maitrise_commandement', aleatoire.randint(5, 10)
    return 'force_caractere', aleatoire.randint(2, 4)


def nouvelles_caracteristiques(aleatoire=None):
    aleatoire = random if aleatoire is None else aleatoire
    nature = tirer_pondere(NATURES, aleatoire)
    orientation = nature.removesuffix('_hybride')
    trait = tirer_pondere(TRAITS[orientation], aleatoire)
    return dict(niveau=0, nature=nature, orientation_principale=orientation, trait_inne=trait,
                points_commandement=gain_commandement(0, aleatoire) if orientation == 'stratege' else 0,
                moral=0, evolutions_acquises=[], evolution_apprise=None,
                progression_combat=0, progression_formation=0, etiquettes={}, etiquettes_permanentes=[])


def emplacements_etiquettes(niveau):
    """Un emplacement initial, puis un supplémentaire tous les cinq niveaux."""
    if type(niveau) is not int or niveau < 0:
        raise ValueError('Niveau entier positif ou nul requis.')
    return 1 + niveau // 5


def niveau_max_etiquette(niveau):
    """Niveau 1 initial ; niveau 2 dès le niveau 5, etc."""
    return emplacements_etiquettes(niveau)


def apprendre_etiquette(fiche, identifiant):
    """Apprentissage après validation du séjour à l'École des officiers.

    Renvoie une nouvelle fiche sans modifier l'original. L'intégration dans
    le cycle de validation de l'École reste une étape distincte.
    """
    resultat = deepcopy(fiche)
    if identifiant not in catalogues.ETIQUETTES_COMBAT:
        raise ValueError('Étiquette inconnue du catalogue scolaire.')
    if identifiant in resultat.get('etiquettes_permanentes', []):
        raise ValueError('Étiquette permanente : modification interdite à l’École.')
    niveaux = resultat.setdefault('etiquettes', {})
    actuel = niveaux.get(identifiant, 0)
    if actuel:
        if actuel >= niveau_max_etiquette(resultat['niveau']):
            raise ValueError('Niveau maximal de cette étiquette déjà atteint.')
        niveaux[identifiant] = actuel + 1
    else:
        if len(niveaux) - len(resultat.get('etiquettes_permanentes', [])) >= emplacements_etiquettes(resultat['niveau']):
            raise ValueError('Aucun emplacement d’étiquette disponible.')
        niveaux[identifiant] = 1
    return resultat


def capacite_maximale(fiche):
    """Capacité propre au général : +2 par niveau gagné après zombification."""
    import config
    if fiche and fiche.get('etat_zombie'):
        return config.max_unites_par_general + 2 * fiche.get('niveaux_zombie', 0)
    return config.max_unites_par_general


def capacite_maximale_general(general):
    return capacite_maximale(caracteristiques_general(general))


def evolutions_eligibles(fiche, catalogue=None, apprentissage=True):
    catalogue = catalogues.EVOLUTIONS if catalogue is None else catalogue
    resultat = {}
    for identifiant, evolution in catalogue.items():
        if not evolution['disponible']:
            continue
        if not compatible(fiche, evolution['natures'], apprentissage):
            continue
        categorie = evolution['categorie']
        if categorie == 'moral' and fiche['moral'] >= 100:
            continue
        if categorie == 'unite' and identifiant in fiche['evolutions_acquises']:
            continue
        resultat[identifiant] = evolution
    return resultat


def monter_niveau(fiche, aleatoire=None, catalogue=None, choisir_evolution=None):
    """Progression naturelle à chaque niveau ; roulette sauf tous les cinq niveaux.

    Aux paliers de cinq, obtention d'une étiquette permanente (non modifiable
    à l'École). Les évolutions d'unités restent autorisées aux autres niveaux.
    """
    aleatoire = random if aleatoire is None else aleatoire
    resultat = deepcopy(fiche)
    resultat['niveau'] += 1
    niveau = resultat['niveau']
    if resultat.get('etat_zombie'):
        resultat['niveaux_zombie'] = resultat.get('niveaux_zombie', 0) + 1
        return resultat, None

    orientation = orientation_principale(resultat)
    if orientation == 'stratege':
        resultat['points_commandement'] += gain_pc_naturel(aleatoire)
    else:
        resultat['moral'] = min(100, resultat['moral'] + gain_moral_naturel(niveau))

    if niveau % 5 == 0:
        permanentes = resultat.setdefault('etiquettes_permanentes', [])
        disponibles = [nom for nom in catalogues.ETIQUETTES_COMBAT
                       if nom not in resultat.get('etiquettes', {})]
        if disponibles:
            choix = disponibles[aleatoire.randint(0, len(disponibles) - 1)]
            resultat.setdefault('etiquettes', {})[choix] = 1
            permanentes.append(choix)
            return resultat, ('etiquette_permanente', choix)
        return resultat, None

    eligibles = evolutions_eligibles(resultat, catalogue, apprentissage=False)
    # Les catégories de statistiques restent dans la roulette uniquement si
    # leur récompense est utilisable ; une unité déjà acquise ne revient pas.
    poids = RECOMPENSES[orientation][resultat['trait_inne']]
    poids = {categorie: chance for categorie, chance in poids.items()
             if any(e['categorie'] == categorie for e in eligibles.values())}
    if not poids:
        return resultat, None
    categorie = tirer_pondere(poids, aleatoire)
    candidats = [i for i, e in eligibles.items() if e['categorie'] == categorie]
    if len(candidats) == 1:
        identifiant = candidats[0]
    elif choisir_evolution is not None:
        identifiant = choisir_evolution(tuple(candidats), aleatoire)
        if identifiant not in candidats:
            raise ValueError('Évolution sélectionnée hors catalogue éligible.')
    else:
        identifiant = candidats[aleatoire.randint(0, len(candidats) - 1)]
    if categorie in ('commandement', 'moral'):
        nom, gain = recompense_statistique(orientation, aleatoire)
        if categorie == 'commandement':
            resultat['points_commandement'] += gain
        else:
            resultat['moral'] = min(100, resultat['moral'] + gain)
        return resultat, (nom, gain)
    if identifiant not in resultat['evolutions_acquises']:
        resultat['evolutions_acquises'].append(identifiant)
    return resultat, identifiant


def progression_due(fiche, observations, condition=None):
    """Compatibilité des conditions administratives ; aucun compteur brut ne fait foi.

    Le pilote valide désormais les événements par valider_evenement, après les
    preuves de combat ou de séjour. Cette API seule n'accorde aucun niveau.
    """
    return bool(condition and condition(deepcopy(fiche), deepcopy(observations)))


def charger():
    import config
    chemin = config.racine_metier() / '.systeme/progression.json'
    return json.loads(chemin.read_text(encoding='utf-8')) if chemin.exists() else {}


def sauvegarder(donnees):
    import config
    import etat
    etat.ecrire_prive(config.racine_metier() / '.systeme/progression.json',
                      json.dumps(donnees, ensure_ascii=False) + '\n')


def caracteristiques_general(general):
    """La fiche possédée par le joueur n'est jamais une autorité de gameplay."""
    return deepcopy(charger().get(f"{general['joueur']}:{general['nom']}"))


def enregistrer_creation(joueur, nom, caracteristiques):
    donnees = charger()
    identifiant = f'{joueur}:{nom}'
    if identifiant not in donnees:
        donnees[identifiant] = deepcopy(caracteristiques)
        sauvegarder(donnees)
    return deepcopy(donnees[identifiant])


def publier_fiche(chemin_general, caracteristiques):
    """Met à jour seulement les champs moteur, conserve les anciens attributs."""
    import os
    import stat
    chemin = chemin_general / 'fiche.txt'
    for p in (chemin, *chemin.parents):
        if p.is_symlink():
            raise RuntimeError(f'Fiche liée interdite : {chemin}')
    if chemin.exists() and (not stat.S_ISREG(chemin.stat().st_mode) or chemin.stat().st_nlink != 1):
        raise RuntimeError(f'Fiche non ordinaire : {chemin}')
    lignes = chemin.read_text(encoding='utf-8').splitlines() if chemin.exists() else []
    lignes = [l for l in lignes if l.split('=', 1)[0].strip() not in caracteristiques]
    for cle, valeur in caracteristiques.items():
        if cle in ('apprentissages_valides', 'progressions_validees'):
            continue  # Journal de reprise privé, sans utilité dans la fiche joueur.
        if isinstance(valeur, list):
            valeur = ','.join(map(str, valeur))
        elif valeur is None:
            valeur = ''
        lignes.append(f'{cle}={valeur}')
    fd = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as fichier:
        fichier.write('\n'.join(lignes) + '\n')


def attribuer_niveau(general, aleatoire=None, catalogue=None, choisir_evolution=None):
    donnees = charger()
    identifiant = f"{general['joueur']}:{general['nom']}"
    if identifiant not in donnees:
        raise ValueError('Ancien général sans caractéristiques : migration explicite nécessaire.')
    nouvelle, recompense = monter_niveau(donnees[identifiant], aleatoire, catalogue, choisir_evolution)
    donnees[identifiant] = nouvelle
    sauvegarder(donnees)
    publier_fiche(general['chemin'], nouvelle)
    return recompense


def valider_evenement(general, voie, evenement, aleatoire=None):
    """Un événement moteur attesté ; jauge, récompense et reçu atomiques.

    Une reprise après l'enregistrement répare seulement la copie joueur. Les
    anciens généraux sans profil ne reçoivent aucune caractéristique inventée.
    """
    seuil = SEUILS[voie]
    donnees = charger()
    identite = f"{general['joueur']}:{general['nom']}"
    fiche = donnees.get(identite)
    if fiche is None:
        return False
    cle = f'{voie}:{evenement}'
    if cle in fiche.get('progressions_validees', {}):
        publier_fiche(general['chemin'], fiche)
        return False
    fiche = deepcopy(fiche)
    for source in SEUILS:
        fiche.setdefault(f'progression_{source}', 0)
    jauge = f'progression_{voie}'
    fiche[jauge] += 1
    recompense = None
    if fiche[jauge] == seuil:
        fiche, recompense = monter_niveau(
            fiche, aleatoire_progression if aleatoire is None else aleatoire)
        fiche[jauge] = 0
    fiche.setdefault('progressions_validees', {})[cle] = {
        'niveau': fiche['niveau'], 'recompense': recompense}
    donnees[identite] = fiche
    sauvegarder(donnees)
    publier_fiche(general['chemin'], fiche)
    return True
