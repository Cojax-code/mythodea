"""Caractéristiques et récompenses des généraux ; aucun barème automatique."""
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
        'charismatique': {'commandement': 60, 'ordre': 30, 'unite': 10},
        'leader': {'commandement': 20, 'ordre': 70, 'unite': 10},
        'inventeur': {'commandement': 20, 'ordre': 20, 'unite': 60},
    },
    'instinctif': {
        'charismatique': {'moral': 60, 'ordre': 15, 'unite': 25},
        'leader': {'moral': 20, 'ordre': 60, 'unite': 20},
        'inventeur': {'moral': 20, 'ordre': 10, 'unite': 70},
    },
}


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


def nouvelles_caracteristiques(aleatoire=None):
    aleatoire = random if aleatoire is None else aleatoire
    nature = tirer_pondere({'stratege': 50, 'instinctif': 50}, aleatoire)
    trait = tirer_pondere(TRAITS[nature], aleatoire)
    return dict(niveau=0, nature=nature, trait_inne=trait,
                points_commandement=gain_commandement(0, aleatoire) if nature == 'stratege' else 0,
                moral=0, evolutions_acquises=[], evolution_apprise=None)


def evolutions_eligibles(fiche, catalogue=None):
    catalogue = catalogues.EVOLUTIONS if catalogue is None else catalogue
    resultat = {}
    for identifiant, evolution in catalogue.items():
        if not evolution['disponible']:
            continue
        if evolution['natures'] is not None and fiche['nature'] not in evolution['natures']:
            continue
        categorie = evolution['categorie']
        if categorie == 'moral' and fiche['moral'] >= 100:
            continue
        if categorie in ('unite', 'ordre') and identifiant in fiche['evolutions_acquises']:
            continue
        resultat[identifiant] = evolution
    return resultat


def monter_niveau(fiche, aleatoire=None, catalogue=None, choisir_evolution=None):
    """Un appel administratif/moteur = un niveau, sans condition implicite.

    Le choix entre plusieurs évolutions d'une catégorie reste injecté : aucun
    poids interne au futur catalogue d'unités ou d'ordres n'est encore défini.
    Retourne une copie ; le demandeur persiste le résultat après validation.
    """
    aleatoire = random if aleatoire is None else aleatoire
    resultat = deepcopy(fiche)
    eligibles = evolutions_eligibles(resultat, catalogue)
    identifiant = resultat.get('evolution_apprise')
    if identifiant is not None and identifiant not in eligibles:
        raise ValueError('Évolution mémorisée incompatible ou indisponible ; progression conservée.')
    if identifiant is None:
        poids = RECOMPENSES[resultat['nature']][resultat['trait_inne']]
        poids = {categorie: p for categorie, p in poids.items()
                 if any(e['categorie'] == categorie for e in eligibles.values())}
        if poids:
            categorie = tirer_pondere(poids, aleatoire)
            candidats = [i for i, e in eligibles.items() if e['categorie'] == categorie]
            if len(candidats) == 1:
                identifiant = candidats[0]
            elif choisir_evolution is not None:
                identifiant = choisir_evolution(tuple(candidats), aleatoire)
                if identifiant not in candidats:
                    raise ValueError('Évolution sélectionnée hors catalogue éligible.')
            else:
                raise ValueError('Règle de choix dans la catégorie à configurer.')
    resultat['niveau'] += 1
    if identifiant is not None:
        categorie = eligibles[identifiant]['categorie']
        if categorie == 'commandement':
            resultat['points_commandement'] += gain_commandement(resultat['niveau'], aleatoire)
        elif categorie == 'moral':
            resultat['moral'] = min(100, resultat['moral'] + 1 + aleatoire.randint(0, resultat['niveau']))
        if identifiant not in resultat['evolutions_acquises']:
            resultat['evolutions_acquises'].append(identifiant)
        resultat['evolution_apprise'] = None
    return resultat, identifiant


def progression_due(fiche, observations, condition=None):
    """Aucun niveau automatique tant qu'un barème n'a pas été configuré."""
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
        if cle == 'apprentissages_valides':
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
