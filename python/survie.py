"""Cycle Survie Est : fenêtres d'action, progression, vagues et cascades."""
import grp
import os
import pwd
import time

import config
import combats
import etat
import generaux
import mouvements
import rapports
import vagues
import plateau
import securite
import minuterie
import crypte


ORDRE_RESOLUTION_EST = ("village", "est_1", "est_2", "est_3")
ORDRE_APPARITION_EST = ("est_3", "est_2", "est_1")


def profil_survie(configuration=None):
    if configuration is None:
        configuration = config.configuration_mode("survie")
    if configuration["mode"] != "survie":
        raise ValueError("La phase ennemie Est exige le profil Survie.")
    return configuration


def verifier_plateau_dedie(configuration):
    """Refuse un mélange avec une partie classique, sans effacer ses données."""
    config.verifier_structure_actuelle(configuration)
    for nom in config.configuration_mode('classique')['carte_territoires']:
        for chemin in (configuration['game_path'] / nom,
                       config.rapports_territoires_dir / (nom + '.txt')):
            if chemin.exists() or chemin.is_symlink():
                raise RuntimeError(
                    'Le mode Survie exige un plateau dédié sans vestiges du mode classique. '
                    'Faire archiver le plateau et ses rapports par un administrateur avant le lancement.')


def preparer_zones_bot(configuration):
    """Crée les zones privées du bot, sans toucher aux forces présentes."""
    acteur = configuration["acteurs"]["bot"]
    uid = pwd.getpwnam(acteur["proprietaire_linux"]).pw_uid
    gid = grp.getgrnam(acteur["groupe_linux"]).gr_gid
    for territoire in configuration["territoires"]:
        territoire.mkdir(parents=True, exist_ok=True)
        dossiers = [territoire / "bot"]
        dossiers.extend(zone["chemin"] for zone in
                        generaux.zones_generaux_territoire(territoire, "bot", configuration))
        for dossier in dossiers:
            dossier.mkdir(mode=0o700, exist_ok=True)
            os.chown(dossier, uid, gid)
            os.chmod(dossier, 0o700)


def inventorier_ennemis(territoire, configuration=None):
    """Lit toutes les présences, y compris les renforts, sans nettoyage."""
    configuration = profil_survie(configuration)
    inventaire = []
    for zone in generaux.zones_generaux_territoire(territoire, "bot", configuration):
        if not zone["chemin"].exists():
            continue
        for chemin in zone["chemin"].iterdir():
            if chemin.is_dir() and generaux.numero_general_depuis_nom(chemin.name) is not None:
                inventaire.append({
                    "chemin": chemin, "nom": chemin.name, "joueur": "bot",
                    "camp": configuration["acteurs"]["bot"]["camp"],
                    "territoire": territoire.name,
                    "emplacement": zone.get("emplacement"),
                    "fiche": generaux.lire_fiche_general(chemin),
                })
    rangs_renforts = {chemin.name: rang for rang, chemin in
                     enumerate(generaux.lire_renforts_bot(territoire))}
    return sorted(inventaire, key=lambda general: (
        general["emplacement"] is None,
        int(general["emplacement"]) if general["emplacement"] is not None
        else rangs_renforts[general["nom"]],
        generaux.numero_general_depuis_nom(general["nom"]),
    ))


def destination_ennemi(territoire, nom, configuration):
    """Utilise une place vide, sinon conserve le général parmi les renforts."""
    zones = generaux.zones_generaux_territoire(territoire, "bot", configuration)
    for zone in zones:
        if (zone["chemin"] / nom).exists():
            raise FileExistsError(f"Identité ennemie déjà présente : {nom}")
    # Les présents passent avant toute nouvelle arrivée dans la colonne.
    generaux.remonter_renforts_bot(territoire, configuration)
    for zone in zones:
        if "emplacement" in zone and not any(zone["chemin"].iterdir()):
            return zone["chemin"] / nom
    return territoire / "bot" / "renforts" / nom


def enregistrer_arrivee_ennemi(territoire, chemin, configuration):
    if chemin.parent.name != "renforts":
        return
    # Un petit numéro arrivant tard reste derrière les renforts déjà présents.
    precedents = [p for p in generaux.lire_renforts_bot(territoire) if p != chemin]
    generaux.sauvegarder_ordre_renforts_bot(territoire, [*precedents, chemin], configuration)


def allies_presents(territoire, configuration):
    """Même présence active que le contrôle commun, sans rejouer son audit."""
    for joueur in configuration['joueurs']:
        for zone in generaux.zones_generaux_territoire(territoire, joueur, configuration):
            if zone.get('emplacement') not in configuration['emplacements'] or not zone['chemin'].exists():
                continue
            if any(p.is_dir() and generaux.numero_general_depuis_nom(p.name) is not None
                   and generaux.contient_unites(p) for p in zone['chemin'].iterdir()):
                return True
    return False


def preparer_deplacements_ennemis(configuration=None, rattrapage=None):
    """Plan complet calculé sans mutation à partir d'un seul inventaire initial."""
    configuration = profil_survie(configuration)
    racine = configuration["game_path"]
    initial = {nom: inventorier_ennemis(racine / nom, configuration)
               for nom in ORDRE_RESOLUTION_EST}
    presences = {nom: allies_presents(racine / nom, configuration) for nom in initial}
    controles_bot = {nom: not presences[nom] and any(
        g['emplacement'] in configuration['emplacements'] and generaux.contient_unites(g['chemin'])
        for g in initial[nom]) for nom in initial}
    destinations = {}
    bloques = {}
    for index, origine in enumerate(ORDRE_RESOLUTION_EST):
        for general in initial[origine]:
            destination = origine
            if index and rattrapage is not None:
                if rattrapage.get(general['nom']) == origine and controles_bot[origine]:
                    destination = ORDRE_RESOLUTION_EST[index - 1]
            elif index:
                if presences[origine]:
                    bloques[general['nom']] = origine
                else:
                    destination = ORDRE_RESOLUTION_EST[index - 1]
            destinations[general['nom']] = destination
    mouvements_prepares = []
    files = {}
    for index, destination in enumerate(ORDRE_RESOLUTION_EST):
        presents = [g for g in initial[destination] if destinations[g['nom']] == destination]
        arrivants = ([g for g in initial[ORDRE_RESOLUTION_EST[index + 1]]
                      if destinations[g['nom']] == destination] if index < 3 else [])
        occupees = {g["emplacement"] for g in presents if g["emplacement"] is not None}
        files[destination] = []
        for general in [*presents, *arrivants]:
            if general in presents and general["emplacement"] is not None:
                chemin = general["chemin"]
            else:
                place = next((p for p in configuration["emplacements"] if p not in occupees), None)
                if place is None:
                    chemin = racine / destination / "bot/renforts" / general["nom"]
                    files[destination].append(chemin)
                else:
                    occupees.add(place)
                    chemin = racine / destination / "bot" / place / general["nom"]
            mouvements_prepares.append({"nom": general["nom"], "origine": general["territoire"],
                                        "destination": destination, "source": general["chemin"],
                                        "chemin": chemin})
    return {"mouvements": mouvements_prepares, "files": files, "bloques": bloques}


def appliquer_deplacements_ennemis(plan, configuration):
    for mouvement in plan["mouvements"]:
        if not mouvement["source"].is_dir():
            raise FileNotFoundError(mouvement["source"])
        if mouvement["source"] != mouvement["chemin"] and mouvement["chemin"].exists():
            raise FileExistsError(mouvement["chemin"])
    positions = etat.charger_positions_generaux()
    for mouvement in plan["mouvements"]:
        if mouvement["source"] != mouvement["chemin"]:
            mouvement["source"].rename(mouvement["chemin"])
        positions[f"bot:{mouvement['nom']}"] = mouvement["destination"]
    etat.sauvegarder_positions_generaux(positions)
    for nom, file in plan["files"].items():
        generaux.sauvegarder_ordre_renforts_bot(configuration["game_path"] / nom, file, configuration)
    return [{k: v for k, v in m.items() if k != "source"} for m in plan["mouvements"]
            if m["origine"] != m["destination"]]


def avancer_ennemis(configuration=None, bloques=None):
    configuration = profil_survie(configuration)
    preparer_zones_bot(configuration)
    plan = preparer_deplacements_ennemis(configuration)
    if bloques is not None:
        bloques.update(plan['bloques'])
    return appliquer_deplacements_ennemis(plan, configuration)


def rattraper_ennemis(bloques, configuration):
    """Une tentative réservée aux survivants bloqués avant les combats.

    La destination peut devenir contestée : aucun nouveau combat ici. Le plan
    repose sur un inventaire unique, même si plusieurs colonnes se rejoignent.
    """
    if not bloques:
        return []
    plan = preparer_deplacements_ennemis(configuration, rattrapage=bloques)
    deplacements = appliquer_deplacements_ennemis(plan, configuration)
    for mouvement in deplacements:
        rapports.ecrire_rapport_court(
            f"Rattrapage bot {mouvement['nom']} : {mouvement['origine']} -> {mouvement['destination']}.")
    return deplacements


def creer_vague_est(numero, configuration=None, aleatoire=None):
    """Matérialise les compositions avec les identités et généraux communs."""
    configuration = profil_survie(configuration)
    compositions = vagues.composer_vague_est(numero, aleatoire)
    preparer_zones_bot(configuration)
    crees = {}
    # Attribuer les identités dans l'ordre canonique avant de matérialiser.
    premier = etat.lire_compteur_general("bot") + 1
    etiquetees = [(premier + index, composition) for index, composition in enumerate(compositions)]
    etat.sauvegarder_compteur_general("bot", premier + len(compositions) - 1)
    equipements = {"archer": ("infanterie", "arc"),
                   "piquier": ("infanterie", "pique"),
                   "cavalier": ("cavalerie", "cheval")}
    for identifiant, composition in sorted(etiquetees, key=lambda item:
            ORDRE_APPARITION_EST.index(item[1]["territoire"])):
        nom = f"general{identifiant}"
        territoire = configuration["game_path"] / composition["territoire"]
        chemin = destination_ennemi(territoire, nom, configuration)
        # Réserver le numéro avant l'écriture : un numéro ne sera jamais réutilisé.
        generaux.creer_general(chemin, nom)
        fiche = chemin / "fiche.txt"
        with fiche.open("a", encoding="utf-8") as fichier:
            fichier.write(f"\nfaction=est\nvague={numero}\n"
                          f"nom_affichage={composition['nom_affichage']}\n")
        for bloc, infos in composition["blocs"].items():
            if not infos["nombre"]:
                continue
            prefixe, equipement = equipements[infos["type"]]
            for index in range(1, infos["nombre"] + 1):
                unite = chemin / bloc / f"{prefixe}{index}"
                unite.mkdir()
                (unite / equipement).touch()
        generaux.donner_permissions_general(
            chemin, configuration["acteurs"]["bot"]["proprietaire_linux"])
        enregistrer_arrivee_ennemi(territoire, chemin, configuration)
        positions = etat.charger_positions_generaux()
        positions[f"bot:{nom}"] = territoire.name
        etat.sauvegarder_positions_generaux(positions)
        crees[identifiant] = chemin
    return [crees[identifiant] for identifiant, _ in etiquetees]


def preparer_phase_ennemie(numero_vague, configuration=None, aleatoire=None):
    """À appeler après l'audit joueur et avant les combats, avec la vague tour+1.

    L'appelant fournit le numéro de vague. Aucun chronomètre, combat,
    contrôle territorial ou déclenchement de défaite n'est effectué ici.
    """
    configuration = profil_survie(configuration)
    if type(numero_vague) is not int or numero_vague < 1:
        raise ValueError("Le numéro de vague doit être un entier positif.")
    deplacements = avancer_ennemis(configuration)
    nouveaux = creer_vague_est(numero_vague, configuration, aleatoire)
    return {"deplacements": deplacements, "nouveaux": nouveaux}


def resoudre_cascade(territoire, configuration=None, mode_combat="OFF/OFF", en_cours_de_fuite=None):
    """Enchaîne les affrontements communs, avec décisions entre deux seulement.

    L'appel ne déplace pas le bot, ne crée aucune vague et ne lance aucun tour.
    Chaque affrontement conserve les pertes sur disque et remonte la colonne.
    """
    configuration = profil_survie(configuration)
    if en_cours_de_fuite is not None:
        configuration = dict(configuration)
        configuration["generaux_hors_combat"] = {
            f"{g['joueur']}:{g['nom']}" for g, _ in en_cours_de_fuite}
    if mode_combat not in ("OFF/OFF", "OFF/DEF"):
        raise ValueError("Mode d'affrontement inconnu.")
    camp_bot = configuration["acteurs"]["bot"]["camp"]
    camp_allie = configuration["acteurs"][configuration["joueurs"][0]]["camp"]
    generaux.remonter_renforts_bot(territoire, configuration)
    forces = generaux.lire_forces_territoire(territoire, configuration)
    for general in generaux.generaux_actifs_joueur(forces, camp_allie):
        generaux.assurer_ordre_surnombre(
            general["chemin"], general["joueur"], territoire.name, configuration)
    affrontements = 0
    retraites = []
    while (generaux.generaux_actifs_joueur(forces, camp_allie)
           and generaux.generaux_actifs_joueur(forces, camp_bot)):
        affrontements += 1
        titre = f"=== AFFRONTEMENT SURVIE {affrontements} : {territoire.name} ==="
        rapports.ecrire_rapport_territoire(territoire, titre)
        rapports.afficher_et_ecrire(titre)
        promus = combats.resoudre_combat_range(territoire, mode_combat, configuration)
        forces = generaux.lire_forces_territoire(territoire, configuration)
        allies = generaux.generaux_actifs_joueur(forces, camp_allie)
        ennemis = generaux.generaux_actifs_joueur(forces, camp_bot)
        if not allies or not ennemis or not promus:
            break

        # Le choix est individuel et n'est lu qu'après la remontée des renforts.
        fuyards = [general for general in allies
                   if generaux.lire_ordre_surnombre(general, territoire.name, configuration) == 1
                   and territoire.name not in configuration["villages"]]
        if en_cours_de_fuite is None:
            destinations = mouvements.retraites_surnombre(fuyards, territoire, configuration)
        else:
            destinations = []
            if fuyards:
                arrivee = mouvements.destination_retraite_surnombre(territoire.name, configuration)
                forces_arrivee = generaux.lire_forces_territoire(configuration["game_path"] / arrivee, configuration)
                if generaux.generaux_actifs_joueur(forces_arrivee, camp_bot):
                    rapports.afficher_et_ecrire(
                        f"Retraite impossible depuis {territoire.name} : bot actif sur {arrivee}.")
                else:
                    destinations = mouvements.preparer_retraites_surnombre(
                        fuyards, territoire, configuration, en_cours_de_fuite)
                    en_cours_de_fuite.extend(destinations)
                    configuration["generaux_hors_combat"].update(
                        f"{g['joueur']}:{g['nom']}" for g, _ in destinations)
        for general, destination in destinations:
            retraites.append({"joueur": general["joueur"], "nom": general["nom"],
                              "origine": territoire.name, "chemin": destination})
            arrivee = mouvements.destination_retraite_surnombre(territoire.name, configuration)
            rapports.ecrire_rapport_territoire(
                territoire, f"Retraite {'réservée' if en_cours_de_fuite is not None else 'effectuée'} : "
                f"{general['joueur']} {general['nom']} : "
                f"{territoire.name} -> {arrivee}, position {destination.parent.name}."
            )
        # Relire après les départs : seuls les alliés encore présents combattront.
        forces = generaux.lire_forces_territoire(territoire, configuration)

    controle = generaux.controle_forces(forces)
    rapports.ecrire_rapport_territoire(territoire, f"Fin de cascade : contrôle {controle}.")
    return {"affrontements": affrontements, "retraites": retraites, "controle": controle}


def ouvrir_tour_survie(configuration=None, horloge=None):
    configuration = profil_survie(configuration)
    verifier_plateau_dedie(configuration)
    with etat.verrou_cycle_survie(configuration):
        return _ouvrir_tour_survie(configuration, horloge)


def _ouvrir_tour_survie(configuration, horloge=None):
    """Prépare une seule fois les généraux et ouvre la fenêtre d'action."""
    configuration = profil_survie(configuration)
    config.verifier_structure_actuelle(configuration)
    horloge = time.time if horloge is None else horloge
    duree = minuterie.valider_duree(configuration["duree_phase_action_secondes"])
    cycle = etat.charger_cycle_survie(configuration)
    if cycle is not None and cycle["phase"] in ("actions", "defaite"):
        return cycle
    if cycle is not None and cycle["phase"] != "a_preparer":
        raise RuntimeError("Cycle interrompu : vérifier le plateau avant de reprendre.")
    tour = 0 if cycle is None else cycle["tour"]
    precedent = cycle or {}
    preparation = {'tour': tour, 'phase': 'preparation'}
    if 'generation_active' in precedent:
        preparation['generation_active'] = precedent['generation_active']
    etat.sauvegarder_cycle_survie(preparation, configuration)
    plateau.reparer_structure(configuration)
    preparer_zones_bot(configuration)
    crypte.preparer(configuration)
    plateau.preparer_accueil(configuration, tour)
    for joueur in configuration["joueurs"]:
        generaux.faire_apparaitre_general_si_possible(joueur, configuration)
    generaux.scanner_ordres_surnombre(configuration)
    cycle = {"tour": tour, "phase": "actions", "echeance": horloge() + duree}
    precedent = etat.charger_cycle_survie(configuration) or {}
    if 'generation_active' in precedent:
        cycle['generation_active'] = precedent['generation_active']
    etat.sauvegarder_cycle_survie(cycle, configuration)
    rapports.afficher_et_ecrire(f"Tour {tour} : fenêtre d'action de {duree:g} secondes.")
    return cycle


def creer_gestion(configuration, horloge=None, dormir=None):
    from cycle_linux import Generations
    return Generations(configuration, horloge=horloge, dormir=dormir)


def resoudre_tour_survie(configuration=None, aleatoire=None, gestion=None):
    """Clôture et résout un tour ; backend/horloges injectables sans attente en test."""
    configuration = profil_survie(configuration)
    verifier_plateau_dedie(configuration)
    with etat.verrou_cycle_survie(configuration):
        gestion = gestion or creer_gestion(configuration)
        gestion.preparer()
        with rapports.droits_allies(gestion.gid):
            return _clore_tour_survie(configuration, gestion, aleatoire)


def _clore_tour_survie(configuration, gestion, aleatoire=None):
    cycle = etat.charger_cycle_survie(configuration)
    if cycle is None or cycle['phase'] != 'actions':
        raise RuntimeError('Aucune fenêtre ACTIONS à clôturer ; vérifier la récupération.')
    tour = cycle['tour']
    try:
        crypte.verifier_collecteur(configuration)
        prive, homes = gestion.capturer(tour)
        gestion.marquer(tour, 'resolution')
        gestion.afficher(tour, 'resolution', detail='JOUEURS DEGELÉS')
        etat.sauvegarder_cycle_survie({'tour': tour, 'phase': 'actions'}, prive)
        with config.racines_generation(prive['game_path'], homes):
            resultat = _resoudre_tour_capture(prive, aleatoire)
        from cycle_linux import ecrire_json
        ecrire_json(gestion.generation / 'resultat.json',
                    {'tour': tour, 'resolution_terminee': True, 'defaite': resultat['defaite']})
        public, stage = gestion.preparer_publication()
        gestion.publier(tour, public, stage, resultat['defaite'])
        gestion.afficher(tour, 'defaite' if resultat['defaite'] else 'consultation',
                         None if resultat['defaite'] else configuration['duree_consultation_secondes'],
                         'Publication terminée. Faire cd ~ puis revenir sur la carte.')
        return resultat
    except BaseException as erreur:
        gestion.erreur(tour, erreur)
        raise


def _resoudre_tour_capture(configuration, aleatoire=None):
    """Résout une fenêtre d'action ouverte, sans attendre et sans lancer de timer."""
    configuration = profil_survie(configuration)
    config.verifier_structure_actuelle(configuration)
    cycle = etat.charger_cycle_survie(configuration)
    if cycle is None or cycle["phase"] != "actions":
        raise RuntimeError("Aucune fenêtre d'action Survie ouverte à résoudre.")
    tour = cycle["tour"]
    etat.sauvegarder_cycle_survie({"tour": tour, "phase": "resolution"}, configuration)
    rapports.preparer_rapports(configuration)
    rapports.afficher_et_ecrire(f"=== RÉSOLUTION TOUR {tour} / VAGUE {tour + 1} ===")
    controle_avant = etat.charger_controle_territoires(configuration)
    profil_audit = dict(configuration, tour_preparation=(tour == 0))
    securite.verifier_tous_les_deplacements(profil_audit)
    bloques = {}
    deplacements = avancer_ennemis(configuration, bloques)
    securite.controler_coherence_territoires(configuration)
    nouveaux = creer_vague_est(tour + 1, configuration, aleatoire)
    # Assurer une tête de colonne même sur les territoires sans alliés.
    for nom in ORDRE_RESOLUTION_EST:
        generaux.remonter_renforts_bot(configuration["game_path"] / nom, configuration)
    presences = securite.controler_coherence_territoires(configuration)
    conflits = [nom for nom in ORDRE_RESOLUTION_EST if len(presences[nom]) > 1]
    en_cours_de_fuite = []
    batailles = {}
    try:
        for nom in conflits:
            territoire = configuration["game_path"] / nom
            rapports.definir_territoire_rapport(territoire)
            mode = "OFF/DEF" if controle_avant.get(nom) in ("allies", "bot") else "OFF/OFF"
            batailles[nom] = resoudre_cascade(territoire, configuration, mode, en_cours_de_fuite)
    finally:
        rapports.definir_territoire_rapport(None)
    mouvements.appliquer_retraites_surnombre(en_cours_de_fuite, configuration)
    rattrapages = rattraper_ennemis(bloques, configuration)
    securite.controler_coherence_territoires(configuration)
    plateau.sauvegarder_controle_territoires(configuration)
    controle = etat.charger_controle_territoires(configuration)
    defaite = controle["village"] == "bot"
    for nom in ORDRE_RESOLUTION_EST:
        rapports.ecrire_rapport_court(f"{nom} : contrôle final = {controle[nom]}")
    if defaite:
        rapports.afficher_et_ecrire("DÉFAITE : le bot contrôle le village.")
        rapports.ecrire_rapport_court("DÉFAITE : le bot contrôle le village.")
    crypte.materialiser(configuration, tour)
    rapports.ecrire_rapport_court(f"Fin du tour {tour} — vague {tour + 1}.")
    plateau.preparer_accueil(configuration, tour + 1,
                            config.rapport_court_path.read_text(encoding='utf-8'))
    etat.sauvegarder_cycle_survie(
        {"tour": tour if defaite else tour + 1, "phase": "defaite" if defaite else "a_preparer"},
        configuration)
    return {"tour": tour, "vague": tour + 1, "deplacements": deplacements,
            "rattrapages": rattrapages,
            "nouveaux": nouveaux, "batailles": batailles, "retraites": en_cours_de_fuite,
            "controle": controle, "defaite": defaite}


def lancer_partie_survie(configuration=None, nombre_tours=None, horloge=None, dormir=None):
    configuration = profil_survie(configuration)
    verifier_plateau_dedie(configuration)
    with etat.verrou_cycle_survie(configuration):
        with crypte.service(configuration):
            return _lancer_partie_survie(configuration, nombre_tours, horloge, dormir)


def _lancer_partie_survie(configuration, nombre_tours, horloge, dormir):
    """Pilote les fenêtres et la résolution ; l'attente ne connaît aucune règle."""
    configuration = profil_survie(configuration)
    if nombre_tours is not None and (type(nombre_tours) is not int or nombre_tours < 1):
        raise ValueError("Le nombre de tours doit être positif.")
    gestion = creer_gestion(configuration, horloge, dormir)
    gestion.preparer()
    resultats = []
    with rapports.droits_allies(gestion.gid):
        cycle = etat.charger_cycle_survie(configuration)
        nouvelle_partie = cycle is None
        if cycle is None or cycle['phase'] == 'a_preparer':
            cycle = _ouvrir_tour_survie(configuration, horloge)
        if nouvelle_partie:
            gestion.afficher(cycle['tour'], 'actions', max(0, cycle['echeance'] - gestion.horloge()))
            gestion.annoncer_debut()
        while cycle['phase'] != 'defaite' and (nombre_tours is None or len(resultats) < nombre_tours):
            if cycle['phase'] == 'consultation':
                gestion.attendre(cycle)
                try:
                    gestion.permissions_actions()
                except BaseException as erreur:
                    gestion.erreur(cycle['tour'], erreur)
                    raise
                gestion.marquer(cycle['tour'] + 1, 'a_preparer')
                cycle = _ouvrir_tour_survie(configuration, horloge)
            if cycle['phase'] != 'actions':
                raise RuntimeError('Cycle interrompu : récupération administrative requise.')
            # Compléter les documents Crypte lors de la reprise d'une fenêtre.
            crypte.preparer(configuration)
            gestion.attendre(cycle)
            resultat = _clore_tour_survie(configuration, gestion)
            resultats.append(resultat)
            rapports.afficher_fin_de_tour(configuration)
            cycle = etat.charger_cycle_survie(configuration)
    return resultats
