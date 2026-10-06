"""Phase ennemie Est : progression puis apparition, sans cycle de partie."""
import grp
import os
import pwd

import config
import combats
import etat
import generaux
import mouvements
import rapports
import vagues


def profil_survie(configuration=None):
    if configuration is None:
        configuration = config.configuration_mode("survie")
    if configuration["mode"] != "survie":
        raise ValueError("La phase ennemie Est exige le profil Survie.")
    return configuration


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


def avancer_ennemis(configuration=None):
    """Avance chaque ancien ennemi d'une case ; ceux du village y restent."""
    configuration = profil_survie(configuration)
    preparer_zones_bot(configuration)
    racine = configuration["game_path"]
    deplacements = []
    # Du village vers le fond : une arrivée n'est jamais déplacée une seconde fois.
    for origine, destination in (("est_1", "village"), ("est_2", "est_1"),
                                 ("est_3", "est_2")):
        for general in inventorier_ennemis(racine / origine, configuration):
            chemin = destination_ennemi(racine / destination, general["nom"], configuration)
            general["chemin"].rename(chemin)
            enregistrer_arrivee_ennemi(racine / destination, chemin, configuration)
            positions = etat.charger_positions_generaux()
            positions[f"bot:{general['nom']}"] = destination
            etat.sauvegarder_positions_generaux(positions)
            deplacements.append({"nom": general["nom"], "origine": origine,
                                 "destination": destination, "chemin": chemin})
        generaux.sauvegarder_ordre_renforts_bot(racine / origine, [], configuration)
    return deplacements


def creer_vague_est(numero, configuration=None, aleatoire=None):
    """Matérialise les compositions avec les identités et généraux communs."""
    configuration = profil_survie(configuration)
    compositions = vagues.composer_vague_est(numero, aleatoire)
    preparer_zones_bot(configuration)
    crees = []
    equipements = {"archer": ("infanterie", "arc"),
                   "piquier": ("infanterie", "pique"),
                   "cavalier": ("cavalerie", "cheval")}
    for composition in compositions:
        identifiant = etat.lire_compteur_general("bot") + 1
        nom = f"general{identifiant}"
        territoire = configuration["game_path"] / composition["territoire"]
        chemin = destination_ennemi(territoire, nom, configuration)
        # Réserver le numéro avant l'écriture : un numéro ne sera jamais réutilisé.
        etat.sauvegarder_compteur_general("bot", identifiant)
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
        crees.append(chemin)
    return crees


def preparer_phase_ennemie(numero_vague, configuration=None, aleatoire=None):
    """À appeler une fois pour la vague demandée, avant l'audit et les combats.

    Le futur cycle fournira le numéro de vague. Aucun chronomètre, combat,
    contrôle territorial ou déclenchement de défaite n'est effectué ici.
    """
    configuration = profil_survie(configuration)
    if type(numero_vague) is not int or numero_vague < 1:
        raise ValueError("Le numéro de vague doit être un entier positif.")
    deplacements = avancer_ennemis(configuration)
    nouveaux = creer_vague_est(numero_vague, configuration, aleatoire)
    return {"deplacements": deplacements, "nouveaux": nouveaux}


def resoudre_cascade(territoire, configuration=None, mode_combat="OFF/OFF"):
    """Enchaîne les affrontements communs, avec décisions entre deux seulement.

    L'appel ne déplace pas le bot, ne crée aucune vague et ne lance aucun tour.
    Chaque affrontement conserve les pertes sur disque et remonte la colonne.
    """
    configuration = profil_survie(configuration)
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
        destinations = mouvements.retraites_surnombre(fuyards, territoire, configuration)
        for general, destination in destinations:
            retraites.append({"joueur": general["joueur"], "nom": general["nom"],
                              "origine": territoire.name, "chemin": destination})
            arrivee = mouvements.destination_retraite_surnombre(territoire.name, configuration)
            rapports.ecrire_rapport_territoire(
                territoire, f"Retraite : {general['joueur']} {general['nom']} : "
                f"{territoire.name} -> {arrivee}, position {destination.parent.name}."
            )
        # Relire après les départs : seuls les alliés encore présents combattront.
        forces = generaux.lire_forces_territoire(territoire, configuration)

    controle = generaux.controle_forces(forces)
    rapports.ecrire_rapport_territoire(territoire, f"Fin de cascade : contrôle {controle}.")
    return {"affrontements": affrontements, "retraites": retraites, "controle": controle}
