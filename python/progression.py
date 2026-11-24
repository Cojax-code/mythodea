"""Caractéristiques, jauges indépendantes et récompenses officielles des généraux."""
from copy import deepcopy
import json
import random
from contextvars import ContextVar

import catalogues


TRAITS = {
    'stratege': {'charismatique': 50, 'leader': 35, 'inventeur': 15},
    'instinctif': {'charismatique': 50, 'leader': 15, 'inventeur': 35},
    'hybride': {'charismatique': 50, 'leader': 25, 'inventeur': 25},
}
RECOMPENSES = {
    'stratege': {
        'charismatique': {'commandement': 40, 'moral': 10, 'unite': 15, 'etiquette': 35},
        'leader': {'commandement': 35, 'moral': 10, 'unite': 15, 'etiquette': 40},
        'inventeur': {'commandement': 15, 'moral': 10, 'unite': 40, 'etiquette': 35},
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

NATURES = {'stratege': 45, 'instinctif': 45, 'hybride': 10}
VERSION_PROGRESSION = 3
SEUILS = {'combat': 2, 'formation': 3}
# Les récompenses ne modifient pas la suite des tirages des combats.
aleatoire_progression = random.Random()
CHAMPS_HISTORIQUES = frozenset(('orientation', 'strategie', 'force', 'experience',
                               'etiquettes_permanentes', 'orientation_principale'))


def normaliser_profil(fiche):
    """Retire les anciennes clés sans modifier les connaissances ni leurs rangs."""
    resultat = deepcopy(fiche)
    resultat['nature'] = orientation_principale(resultat)
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
    """Compatibilité de l'API : l'Hybride est une orientation sans dominante."""
    nature = fiche['nature']
    return 'hybride' if nature in ('stratege_hybride', 'instinctif_hybride') else nature


def compatible(fiche, natures, apprentissage=True):
    orientation = orientation_principale(fiche)
    return (natures is None or orientation in natures or
            (orientation == 'hybride' and bool(set(natures) & {'stratege', 'instinctif'})))


def capacite_etiquettes_actives(fiche):
    """Les places débloquées sont distinctes des connaissances et de leurs rangs."""
    maximum = 1 if orientation_principale(fiche) == 'instinctif' else 3
    places = fiche.get('emplacements_etiquettes_actives', 1)
    if type(places) is not int or not 1 <= places <= maximum:
        raise ValueError('Nombre officiel d’emplacements actifs invalide.')
    return places


def progression_specifique(fiche, aleatoire):
    """Une étape disponible, sans roulette ni gain naturel ; modifie la copie fournie."""
    orientation = orientation_principale(fiche)
    disponibles = []
    if orientation in ('stratege', 'hybride') and fiche['emplacements_etiquettes_actives'] < 3:
        disponibles.append('stratege')
    if orientation in ('instinctif', 'hybride') and fiche['niveau_etendard'] < 2:
        disponibles.append('instinctif')
    if not disponibles:
        return None, None
    tiree = (tirer_pondere({'stratege': 50, 'instinctif': 50}, aleatoire)
             if orientation == 'hybride' else orientation)
    branche = tiree if tiree in disponibles else disponibles[0]
    basculement = f'{tiree} → {branche}' if branche != tiree else None
    if branche == 'stratege':
        fiche['emplacements_etiquettes_actives'] += 1
        recompense = ('emplacement_actif', fiche['emplacements_etiquettes_actives'])
    else:
        fiche['niveau_etendard'] += 1
        recompense = ('etendard', fiche['niveau_etendard'])
    return recompense, basculement


def migrer_profil(fiche, aleatoire=None):
    """Rattrape une fois les capacités, sans rejouer les anciennes récompenses."""
    resultat = normaliser_profil(fiche)
    if resultat.get('version_progression') == VERSION_PROGRESSION:
        return resultat
    aleatoire = aleatoire_progression if aleatoire is None else aleatoire
    resultat.update(emplacements_etiquettes_actives=1, niveau_etendard=0)
    rattrapage = []
    if resultat.get('etat_zombie'):
        # Conservation de l'ancienne capacité, sans nouvelle récompense zombie.
        resultat['emplacements_etiquettes_actives'] = (
            3 if fiche['nature'] in ('stratege', 'stratege_hybride') else 1)
    else:
        for _ in range(min(4, resultat.get('niveau', 0) // 5)):
            recompense, basculement = progression_specifique(resultat, aleatoire)
            if recompense is not None:
                rattrapage.append(dict(recompense=list(recompense), basculement=basculement))
    resultat['migration_orientations'] = rattrapage
    resultat['version_progression'] = VERSION_PROGRESSION
    return resultat


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


def appliquer_gains_naturels(fiche, aleatoire):
    """Applique les seuls gains du niveau courant, sans tirer de récompense.

    Le niveau doit déjà être incrémenté. Ne modifie pas la fiche reçue.
    Les niveaux zombies sont traités séparément par monter_niveau.
    """
    resultat = deepcopy(fiche)
    if resultat['niveau'] == 0 or resultat.get('etat_zombie'):
        return resultat
    orientation = orientation_principale(resultat)
    hybride = orientation == 'hybride'
    if orientation == 'stratege' or hybride:
        resultat['points_commandement'] += gain_pc_naturel(aleatoire)
    if orientation == 'instinctif' or hybride:
        resultat['moral'] = min(100, resultat['moral'] + gain_moral_naturel(resultat['niveau']))
    return resultat


def recompense_statistique(orientation, aleatoire):
    if orientation == 'stratege':
        return 'maitrise_commandement', aleatoire.randint(5, 10)
    return 'force_caractere', aleatoire.randint(2, 4)


def nouvelles_caracteristiques(aleatoire=None):
    aleatoire = random if aleatoire is None else aleatoire
    nature = tirer_pondere(NATURES, aleatoire)
    orientation = nature
    trait = tirer_pondere(TRAITS[orientation], aleatoire)
    # Au niveau 0, seule l'identité du général est déterminée.
    # Les statistiques, étiquettes et évolutions s'acquièrent par la progression.
    return dict(niveau=0, nature=nature, trait_inne=trait,
                points_commandement=0, moral=0, evolutions_acquises=[], evolution_apprise=None,
                progression_combat=0, progression_formation=0,
                etiquettes={}, etiquettes_apprises_ecole=[],
                emplacements_etiquettes_actives=1, niveau_etendard=0,
                version_progression=VERSION_PROGRESSION)


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
    """Gains naturels, récompense classique, puis supplément tous les cinq niveaux.

    Le retour historique reste la récompense classique. Le bilan complet privé
    accompagne le profil et le reçu atomique de l'événement.
    """
    aleatoire = random if aleatoire is None else aleatoire
    resultat = migrer_profil(fiche, aleatoire)
    resultat.pop('dernier_niveau', None)
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

    avant = resultat
    resultat = appliquer_gains_naturels(resultat, aleatoire)
    gains = {cle: resultat[cle] - avant[cle] for cle in ('points_commandement', 'moral')}
    resultat, classique = recompense_classique(resultat, aleatoire, catalogue, choisir_evolution)
    supplementaire, basculement = None, None
    if niveau % 5 == 0:
        supplementaire, basculement = progression_specifique(resultat, aleatoire)
        if supplementaire is None:
            resultat, supplementaire = recompense_classique(
                resultat, aleatoire, catalogue, choisir_evolution)
    resultat['dernier_niveau'] = dict(niveau=niveau, gains_naturels=gains,
        classique=classique, supplementaire=supplementaire, basculement=basculement)
    return resultat, classique


def recompense_classique(fiche, aleatoire, catalogue=None, choisir_evolution=None):
    """Une mémoire compatible ou une roulette ; aucun gain naturel ni palier."""
    resultat = deepcopy(fiche)
    orientation = orientation_principale(resultat)
    hybride = orientation == 'hybride'
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
    migration = any(f.get('version_progression') != VERSION_PROGRESSION for f in donnees.values())
    resultat = {identite: migrer_profil(fiche) for identite, fiche in donnees.items()}
    if migration:
        # Persister avant toute utilisation : relire ne doit jamais retirer les dés.
        sauvegarder(resultat)
    return resultat


def sauvegarder(donnees):
    import config
    import etat
    donnees = {identite: migrer_profil(fiche) for identite, fiche in donnees.items()}
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
    maximum = capacite_etiquettes_actives(resultat)
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
        if cle in ('apprentissages_valides', 'progressions_validees', 'etiquettes_apprises_ecole',
                   'version_progression', 'migration_orientations', 'dernier_niveau'):
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
    avant = donnees[identifiant]
    nouvelle, recompense = monter_niveau(avant, aleatoire, catalogue, choisir_evolution)
    donnees[identifiant] = nouvelle
    sauvegarder(donnees)
    publier_fiche(general['chemin'], nouvelle)
    import rapports
    rapports.noter_progression(general, avant, nouvelle, 'attribution moteur', recompense)
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
    avant = deepcopy(fiche)
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
    if fiche['niveau'] != avant['niveau'] and 'dernier_niveau' in fiche:
        fiche['progressions_validees'][cle]['bilan'] = deepcopy(fiche['dernier_niveau'])
    donnees[identite] = fiche
    sauvegarder(donnees)
    publier_fiche(general['chemin'], fiche)
    import rapports
    rapports.noter_progression(general, avant, fiche, voie, recompense)
    return True
