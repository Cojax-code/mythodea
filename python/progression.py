"""Caractéristiques, jauges indépendantes et récompenses officielles des généraux."""
from copy import deepcopy
import json
import random
from contextvars import ContextVar

import catalogues


TRAITS = {
    'stratege': {'charismatique': 50, 'leader': 35, 'inventeur': 15},
    'instinctif': {'charismatique': 50, 'leader': 15, 'inventeur': 35},
}
RECOMPENSES = {
    'stratege': {
        'charismatique': {'commandement': 50, 'moral': 0, 'unite': 15, 'etiquette': 35},
        'leader': {'commandement': 45, 'moral': 0, 'unite': 15, 'etiquette': 40},
        'inventeur': {'commandement': 25, 'moral': 0, 'unite': 40, 'etiquette': 35},
    },
    'instinctif': {
        'charismatique': {'commandement': 10, 'moral': 55, 'unite': 20, 'etiquette': 15},
        'leader': {'commandement': 10, 'moral': 50, 'unite': 20, 'etiquette': 20},
        'inventeur': {'commandement': 10, 'moral': 35, 'unite': 40, 'etiquette': 15},
    },
    'hybride': {
        'charismatique': {'commandement': 30, 'moral': 30, 'unite': 15, 'etiquette': 25},
        'leader': {'commandement': 25, 'moral': 30, 'unite': 15, 'etiquette': 30},
        'inventeur': {'commandement': 20, 'moral': 20, 'unite': 35, 'etiquette': 25},
    },
}

NATURES = {'stratege': 45, 'instinctif': 45,
           'stratege_hybride': 5, 'instinctif_hybride': 5}
SEUILS = {'combat': 2, 'formation': 3}
# Les récompenses ne modifient pas la suite des tirages des combats.
aleatoire_progression = random.Random()
CHAMPS_HISTORIQUES = frozenset(('orientation', 'strategie', 'force', 'experience',
                               'etiquettes_permanentes'))


def normaliser_profil(fiche):
    """Retire les anciennes clés sans modifier les connaissances ni leurs rangs."""
    resultat = deepcopy(fiche)
    anciennes = resultat.pop('etiquettes_permanentes', [])
    for nom in anciennes:
        # Les attributions automatiques historiques étaient au rang 1.
        # Un rang déjà enregistré dans etiquettes reste prioritaire.
        resultat.setdefault('etiquettes', {}).setdefault(nom, 1)
    if 'etiquettes_apprises_ecole' not in resultat:
        automatiques = set(anciennes)
        for recu in resultat.get('progressions_validees', {}).values():
            recompense = recu.get('recompense')
            if (isinstance(recompense, (list, tuple)) and len(recompense) == 2
                    and recompense[0] in ('etiquette', 'etiquette_permanente', 'etiquette_zombie')):
                automatiques.add(recompense[1])
        resultat['etiquettes_apprises_ecole'] = [
            nom for nom in resultat.get('etiquettes', {}) if nom not in automatiques]
    for cle in CHAMPS_HISTORIQUES:
        resultat.pop(cle, None)
    return resultat


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
    # Le stratège démarre avec sa première étiquette connue.
    initiale = (list(catalogues.ETIQUETTES_COMBAT)[aleatoire.randint(0, len(catalogues.ETIQUETTES_COMBAT) - 1)]
                if orientation == 'stratege' else None)
    return dict(niveau=0, nature=nature, orientation_principale=orientation, trait_inne=trait,
                points_commandement=gain_commandement(0, aleatoire) if orientation == 'stratege' else 0,
                moral=0, evolutions_acquises=[], evolution_apprise=None,
                progression_combat=0, progression_formation=0,
                etiquettes={initiale: 1} if initiale else {}, etiquettes_apprises_ecole=[])


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
    resultat = normaliser_profil(fiche)
    if identifiant not in catalogues.ETIQUETTES_COMBAT:
        raise ValueError('Étiquette inconnue du catalogue scolaire.')
    niveaux = resultat.setdefault('etiquettes', {})
    actuel = niveaux.get(identifiant, 0)
    if actuel:
        if actuel >= niveau_max_etiquette(resultat['niveau']):
            raise ValueError('Niveau maximal de cette étiquette déjà atteint.')
        niveaux[identifiant] = actuel + 1
    else:
        if orientation_principale(resultat) == 'instinctif' and resultat['niveau'] < 5:
            raise ValueError('L’apprentissage scolaire d’une nouvelle étiquette instinctive exige le niveau 5.')
        if len(resultat['etiquettes_apprises_ecole']) >= emplacements_etiquettes(resultat['niveau']):
            raise ValueError('Aucun emplacement d’étiquette disponible.')
        niveaux[identifiant] = 1
        resultat['etiquettes_apprises_ecole'].append(identifiant)
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
        categorie = evolution['categorie']
        # Les statistiques de roulette suivent la table, indépendamment de la
        # dominante. Les restrictions scolaires et d'unités restent inchangées.
        statistique_roulette = not apprentissage and categorie in ('commandement', 'moral')
        if not statistique_roulette and not compatible(fiche, evolution['natures'], apprentissage):
            continue
        if categorie == 'moral' and fiche['moral'] >= 100:
            continue
        if categorie == 'unite' and identifiant in fiche['evolutions_acquises']:
            continue
        resultat[identifiant] = evolution
    return resultat


def monter_niveau(fiche, aleatoire=None, catalogue=None, choisir_evolution=None):
    """Gain naturel, puis étiquette aux paliers N5/N10 autorisés ou roulette."""
    aleatoire = random if aleatoire is None else aleatoire
    resultat = normaliser_profil(fiche)
    resultat['niveau'] += 1
    niveau = resultat['niveau']
    if resultat.get('etat_zombie'):
        resultat['niveaux_zombie'] = resultat.get('niveaux_zombie', 0) + 1
        # Tirage indépendant de 20 % à chaque niveau, jusqu'à acquisition.
        if 'mort_vivant' not in resultat.get('etiquettes', {}):
            if aleatoire.randint(1, 100) <= 20:
                resultat.setdefault('etiquettes', {})['mort_vivant'] = 1
                return resultat, ('etiquette_zombie', 'mort_vivant')
        return resultat, None

    orientation = orientation_principale(resultat)
    hybride = resultat['nature'].endswith('_hybride')
    if orientation == 'stratege' or hybride:
        resultat['points_commandement'] += gain_pc_naturel(aleatoire)
    if orientation == 'instinctif' or hybride:
        resultat['moral'] = min(100, resultat['moral'] + gain_moral_naturel(niveau))

    # Acquisitions garanties inchangées : création/N5/N10 ou N5 selon la
    # dominante. Les connaissances de roulette ne consomment pas ces paliers.
    # À partir du N15 pour les stratèges, et hors N5 pour les
    # instinctifs, la roulette ordinaire s'applique également aux paliers.
    palier_etiquette = ((orientation == 'stratege' and niveau in (5, 10))
                         or (orientation == 'instinctif' and niveau == 5))
    if palier_etiquette:
        disponibles = [nom for nom in catalogues.ETIQUETTES_COMBAT
                       if nom not in resultat.get('etiquettes', {})]
        if disponibles:
            choix = disponibles[aleatoire.randint(0, len(disponibles) - 1)]
            resultat.setdefault('etiquettes', {})[choix] = 1
            return resultat, ('etiquette', choix)
        # Si toutes les étiquettes sont connues, roulette normale.


    # Une évolution mémorisée à l'École remplace la roulette du prochain
    # niveau où aucune étiquette de palier n'est attribuée.
    manuel = resultat.get('evolution_apprise')
    eligibles = evolutions_eligibles(
        resultat, catalogue, apprentissage=manuel is not None)
    if manuel is not None:
        if manuel not in eligibles:
            raise ValueError('Évolution mémorisée désormais incompatible.')
        identifiant = manuel
        categorie = eligibles[manuel]['categorie']
    else:
        # Les poids sont normalisés sur les récompenses encore accessibles.
        disponibles = [nom for nom in catalogues.ETIQUETTES_COMBAT
                       if nom not in resultat.get('etiquettes', {})]
        poids = RECOMPENSES['hybride' if hybride else orientation][resultat['trait_inne']]
        poids = {categorie: chance for categorie, chance in poids.items()
                 if chance > 0 and (bool(disponibles) if categorie == 'etiquette' else
                                    any(e['categorie'] == categorie for e in eligibles.values()))}
        if not poids:
            # Quand le moral est plafonné et toutes les unités acquises,
            # les PC restent la dernière récompense répétable.
            gain = aleatoire.randint(5, 10)
            resultat['points_commandement'] += gain
            return resultat, ('maitrise_commandement', gain)
        categorie = tirer_pondere(poids, aleatoire)
        if categorie == 'etiquette':
            # Provisoirement : connaissance nouvelle au rang 1 uniquement.
            # L'amélioration d'un rang connu reste réservée à l'École.
            choix = disponibles[aleatoire.randint(0, len(disponibles) - 1)]
            resultat.setdefault('etiquettes', {})[choix] = 1
            return resultat, ('etiquette', choix)
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
        # Une mémoire croisée d'hybride garde le barème de la récompense,
        # indépendamment de l'orientation principale.
        nom, gain = recompense_statistique(
            'stratege' if categorie == 'commandement' else 'instinctif', aleatoire)
        if categorie == 'commandement':
            resultat['points_commandement'] += gain
        else:
            resultat['moral'] = min(100, resultat['moral'] + gain)
        resultat['evolution_apprise'] = None
        return resultat, (nom, gain)
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
    donnees = json.loads(chemin.read_text(encoding='utf-8')) if chemin.exists() else {}
    return {identite: normaliser_profil(fiche) for identite, fiche in donnees.items()}


def sauvegarder(donnees):
    import config
    import etat
    donnees = {identite: normaliser_profil(fiche) for identite, fiche in donnees.items()}
    etat.ecrire_prive(config.racine_metier() / '.systeme/progression.json',
                      json.dumps(donnees, ensure_ascii=False) + '\n')


# Instantané des choix pour la durée du combat territorial.
_SELECTIONS_TERRITORIALES = ContextVar('mythodea_selections_territoriales', default=None)


def figer_selections_territoriales(generaux):
    """Capture les sélections une seule fois, avant le premier affrontement."""
    selections = {}
    for general in generaux:
        fiche = charger().get(f"{general['joueur']}:{general['nom']}")
        if fiche is not None:
            choix = selection_etiquettes(fiche, general['chemin'])
            selections[(general['joueur'], general['nom'])] = tuple(choix['etiquettes_actives'])
    return _SELECTIONS_TERRITORIALES.set(selections)


def retablir_selections_territoriales(jeton):
    _SELECTIONS_TERRITORIALES.reset(jeton)


def selection_etiquettes(fiche, chemin_general):
    """Applique une sélection joueur sans jamais modifier les connaissances privées.

    etiquettes_actives.txt : noms d'étiquettes connus, séparés par lignes ou
    virgules. En son absence, les anciennes fiches restent compatibles.
    """
    import os
    import stat
    selection = chemin_general / 'etiquettes_actives.txt'
    if any(parent.is_symlink() for parent in selection.parents):
        raise ValueError('Sélection sous un dossier lié interdite.')
    resultat = deepcopy(fiche)
    connues = resultat.get('etiquettes', {})
    orientation = orientation_principale(resultat)
    maximum = 3 if orientation == 'stratege' else 1
    speciale = {'mort_vivant'} if resultat.get('etat_zombie') else set()
    try:
        info = selection.lstat()
    except FileNotFoundError:
        ordinaires = [nom for nom in connues if nom not in speciale][:maximum]
        actives = [nom for nom in connues if nom in ordinaires or nom in speciale]
    else:
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('Sélection d’étiquettes liée ou non ordinaire interdite.')
        # Contrôler l'objet ouvert, pas seulement le chemin inspecté avant lui.
        # NONBLOCK empêche un remplacement par FIFO de bloquer le moteur.
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        fd = os.open(selection, flags)
        with os.fdopen(fd, 'r', encoding='utf-8') as fichier:
            ouverte = os.fstat(fichier.fileno())
            if (not stat.S_ISREG(ouverte.st_mode) or ouverte.st_nlink != 1
                    or (ouverte.st_dev, ouverte.st_ino) != (info.st_dev, info.st_ino)):
                raise ValueError('Sélection remplacée ou liée pendant la lecture.')
            contenu = fichier.read()
            finale = os.fstat(fichier.fileno())
            if (finale.st_nlink != 1 or
                    (finale.st_size, finale.st_mtime_ns, finale.st_ctime_ns) !=
                    (ouverte.st_size, ouverte.st_mtime_ns, ouverte.st_ctime_ns)):
                raise ValueError('Sélection modifiée pendant la lecture.')
        actives = [nom.strip() for nom in contenu.replace(',', '\n').splitlines()
                   if nom.strip()]
        if len(actives) != len(set(actives)):
            raise ValueError('Étiquette active sélectionnée plusieurs fois.')
        if any(nom not in connues for nom in actives):
            raise ValueError('Sélection contenant une étiquette non apprise.')
        if sum(nom not in speciale for nom in actives) > maximum:
            raise ValueError('Trop d’étiquettes actives pour cette nature.')
    resultat['etiquettes_actives'] = actives
    return resultat


def caracteristiques_general(general):
    """Les niveaux connus restent privés ; seul le choix d'activation est joueur."""
    fiche = deepcopy(charger().get(f"{general['joueur']}:{general['nom']}"))
    if fiche is None:
        return None
    selections = _SELECTIONS_TERRITORIALES.get()
    identite = (general['joueur'], general['nom'])
    if selections is not None:
        if identite not in selections:
            # Renfort arrivé après le début de la bataille : premier choix figé
            # lors de son premier engagement, sans toucher au QG initial.
            selections[identite] = tuple(selection_etiquettes(fiche, general['chemin'])['etiquettes_actives'])
        fiche['etiquettes_actives'] = list(selections[identite])
        return fiche
    return selection_etiquettes(fiche, general['chemin'])


def enregistrer_creation(joueur, nom, caracteristiques):
    donnees = charger()
    identifiant = f'{joueur}:{nom}'
    if identifiant not in donnees:
        donnees[identifiant] = deepcopy(caracteristiques)
        sauvegarder(donnees)
    return deepcopy(donnees[identifiant])


def publier_fiche(chemin_general, caracteristiques):
    """Publie les champs moteur et retire les clés historiques devenues inutiles."""
    import os
    import stat
    chemin = chemin_general / 'fiche.txt'
    for p in (chemin, *chemin.parents):
        if p.is_symlink():
            raise RuntimeError(f'Fiche liée interdite : {chemin}')
    if chemin.exists() and (not stat.S_ISREG(chemin.stat().st_mode) or chemin.stat().st_nlink != 1):
        raise RuntimeError(f'Fiche non ordinaire : {chemin}')
    lignes = chemin.read_text(encoding='utf-8').splitlines() if chemin.exists() else []
    caracteristiques = normaliser_profil(caracteristiques)
    lignes = [l for l in lignes if l.split('=', 1)[0].strip()
              not in caracteristiques.keys() | CHAMPS_HISTORIQUES]
    for cle, valeur in caracteristiques.items():
        if cle in ('apprentissages_valides', 'progressions_validees', 'etiquettes_apprises_ecole'):
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
