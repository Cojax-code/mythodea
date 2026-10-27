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

NATURES = {'stratege': 45, 'instinctif': 45,
           'stratege_hybride': 5, 'instinctif_hybride': 5}
SEUILS = {'combat': 2, 'formation': 3}
ORDRES_ZOMBIES = ('spora_adicte', 'propagafion')
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


def nouvelles_caracteristiques(aleatoire=None):
    aleatoire = random if aleatoire is None else aleatoire
    nature = tirer_pondere(NATURES, aleatoire)
    orientation = nature.removesuffix('_hybride')
    trait = tirer_pondere(TRAITS[orientation], aleatoire)
    return dict(niveau=0, nature=nature, orientation_principale=orientation, trait_inne=trait,
                points_commandement=gain_commandement(0, aleatoire) if orientation == 'stratege' else 0,
                moral=0, evolutions_acquises=[], evolution_apprise=None,
                progression_combat=0, progression_formation=0)


def capacite_maximale(fiche):
    """Capacité Zombie : +2 par récompense, avec lecture des anciens niveaux.

    L'absence du compteur explicite conserve tous les bonus historiques sans
    réécrire une sauvegarde pendant sa lecture.
    """
    import config
    if est_zombie(fiche):
        gains = fiche.get('gains_capacite_zombie', fiche.get('niveaux_zombie', 0))
        if type(gains) is not int or gains < 0:
            raise ValueError('Compteur de récompenses de capacité Zombie invalide.')
        return config.max_unites_par_general + 2 * gains
    return config.max_unites_par_general


def capacite_maximale_general(general):
    return capacite_maximale(caracteristiques_general(general))


def est_zombie(fiche):
    """Profil spécial dérivé du seul état existant, sans remplacer la nature."""
    return bool(fiche and fiche.get('etat_zombie'))


def ordre_autorise(fiche, nom):
    """Restriction du général Zombie, indépendante du type de ses soldats.

    Le moteur doit fournir le profil privé. Cette condition ne remplace ni
    l'apprentissage, ni la nature, ni la disponibilité dans le catalogue.
    """
    return est_zombie(fiche) == (nom in ORDRES_ZOMBIES)


def reception_ordre_autorisee(fiche, nom):
    """Recevoir un effet allié ne signifie pas apprendre ou émettre cet ordre."""
    return not est_zombie(fiche) or nom in ORDRES_ZOMBIES


def nature_autorise_ordre(fiche, ordre):
    """Politique commune de race et de nature, hors acquisition/disponibilité."""
    if not ordre_autorise(fiche, ordre.get('nom')):
        return False
    if est_zombie(fiche):
        return True
    return ordre['categorie'] != 'globale' or fiche['nature'] in (
        'stratege', 'stratege_hybride', 'instinctif_hybride')


def tirer_recompense_zombie(fiche, aleatoire=None):
    """None = +2 places ; sinon ID appris. Aucun tirage ne peut boucler.

    Sans doublon, deux tirages distincts : 85/15 puis 50/50. Avec un ordre
    connu, le rejet du tirage COMPLET équivaut aux poids 170:15 entre capacité
    et ordre inconnu (85 % contre 7,5 % avant conditionnement).
    """
    aleatoire = random if aleatoire is None else aleatoire
    if not est_zombie(fiche):
        raise ValueError('Récompense réservée au profil Zombie.')
    par_nom = {o['nom']: i for i, o in catalogues.ORDRES.items()}
    ids = [par_nom[nom] for nom in ORDRES_ZOMBIES]
    disponibles = [i for i in ids if i not in fiche['evolutions_acquises']]
    if not disponibles:
        return None
    if len(disponibles) == 1:
        return tirer_pondere({None: 170, disponibles[0]: 15}, aleatoire)
    if tirer_pondere({'capacite': 85, 'ordre': 15}, aleatoire) == 'capacite':
        return None
    return tirer_pondere(dict.fromkeys(ids, 50), aleatoire)


def evolutions_eligibles(fiche, catalogue=None, apprentissage=True):
    catalogue = catalogues.EVOLUTIONS if catalogue is None else catalogue
    resultat = {}
    for identifiant, evolution in catalogue.items():
        if not evolution['disponible']:
            continue
        categorie = evolution['categorie']
        if categorie == 'ordre':
            ordre = catalogues.ORDRES.get(evolution.get('cible', identifiant), {})
            if not ordre_autorise(fiche, ordre.get('nom')):
                continue
        if not (categorie == 'ordre' and est_zombie(fiche)) and not compatible(
                fiche, evolution['natures'], apprentissage):
            continue
        if categorie == 'moral' and fiche['moral'] >= 100:
            continue
        if categorie in ('unite', 'ordre') and identifiant in fiche['evolutions_acquises']:
            continue
        resultat[identifiant] = evolution
    return resultat


def monter_niveau(fiche, aleatoire=None, catalogue=None, choisir_evolution=None):
    """Un appel administratif/moteur = un niveau, sans condition implicite.

    Le choix entre plusieurs évolutions d'une catégorie reste injecté : aucun
    poids particulier n'est appliqué dans une catégorie d'unités ou d'ordres.
    Retourne une copie ; le demandeur persiste le résultat après validation.
    """
    aleatoire = random if aleatoire is None else aleatoire
    resultat = deepcopy(fiche)
    if est_zombie(resultat):
        gains = resultat.get('gains_capacite_zombie', resultat.get('niveaux_zombie', 0))
        if type(gains) is not int or gains < 0:
            raise ValueError('Compteur de récompenses de capacité Zombie invalide.')
        recompense = tirer_recompense_zombie(resultat, aleatoire)
        resultat['niveau'] += 1
        resultat['niveaux_zombie'] = resultat.get('niveaux_zombie', 0) + 1
        resultat['gains_capacite_zombie'] = gains + int(recompense is None)
        if recompense is not None:
            resultat['evolutions_acquises'].append(recompense)
        return resultat, recompense
    eligibles = evolutions_eligibles(resultat, catalogue)
    identifiant = resultat.get('evolution_apprise')
    if identifiant is not None and identifiant not in eligibles:
        raise ValueError('Évolution mémorisée incompatible ou indisponible ; progression conservée.')
    if identifiant is None:
        eligibles = evolutions_eligibles(resultat, catalogue, apprentissage=False)
        poids = RECOMPENSES[orientation_principale(resultat)][resultat['trait_inne']]
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
            elif categorie in ('unite', 'ordre'):
                identifiant = candidats[aleatoire.randint(0, len(candidats) - 1)]
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
