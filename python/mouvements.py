"""Règles de déplacement, marche forcée et envoi au repli."""
import shutil
from collections import deque
import grp
import os
import pwd

import config
import etat
import generaux
import rapports


def delai_sanction_repli(joueur, lieu, configuration):
    """Calcule ceil(distance / 2) sur le graphe du mode, sans déplacer de troupe."""
    retour = configuration["bases_joueurs"][joueur]
    tactiques = {territoire.name for territoire in configuration["territoires"]}
    if lieu not in tactiques:
        raise ValueError(f"Distance de sanction non définie depuis {lieu}.")
    attente = deque([(lieu, 0)])
    visites = {lieu}
    while attente:
        territoire, distance = attente.popleft()
        if territoire == retour:
            return (distance + 1) // 2
        for voisin in configuration["carte_territoires"].get(territoire, []):
            if voisin in tactiques and voisin not in visites:
                visites.add(voisin)
                attente.append((voisin, distance + 1))
    raise ValueError(f"Aucun chemin de retour depuis {lieu} vers {retour}.")


def territoires_adjacents(territoire_depart, territoire_arrivee):
    voisins = config.carte_territoires.get(territoire_depart, [])
    return territoire_arrivee in voisins


def chemin_deux_territoires(
    origine,
    destination,
    configuration=None
):
    # Cherche un territoire intermédiaire permettant :
    # origine -> intermédiaire -> destination.

    carte = config.carte_territoires if configuration is None else configuration["carte_territoires"]
    for intermediaire in carte.get(
        origine,
        []
    ):
        if destination in carte.get(
            intermediaire,
            []
        ):
            return intermediaire

    return None


def verifier_deplacement_general(
    joueur,
    origine,
    destination,
    controle_avant,
    configuration=None
):
    if configuration is None:
        configuration = config.configuration_mode("classique")
    base = configuration["bases_joueurs"][joueur]

    # Aucun déplacement.
    if origine == destination:
        return True, False, "immobile"

    # Première apparition :
    # home -> propre base uniquement.
    if origine == "home":
        if destination == base:
            return True, False, "deploiement"

        return False, False, "sortie du home interdite"

    # Depuis le repli :
    # uniquement vers sa propre base.
    if origine == "repli":
        if destination == base:
            return True, False, "retour de repli"

        return False, False, "sortie du repli interdite"

    # Destination spéciale interdite.
    if destination in ["home", "repli"]:
        return False, False, "destination interdite"

    # Déplacement normal : 1 territoire.
    if destination in configuration["carte_territoires"].get(
        origine,
        []
    ):
        return True, False, "deplacement normal"

    # Marche forcée : 2 territoires.
    intermediaire = chemin_deux_territoires(
        origine,
        destination,
        configuration
    )

    if intermediaire is None:
        return False, False, "destination trop éloignée"

    # Le territoire intermédiaire peut être :
    # - allié ;
    # - neutre.
    #
    # Le passage est interdit uniquement s'il est
    # contrôlé par l'ennemi.

    controle_intermediaire = controle_avant.get(
        intermediaire,
        "neutre"
    )

    acteurs = configuration["acteurs"]
    camp_joueur = acteurs[joueur]["camp"]
    camps_ennemis = {acteur["camp"] for acteur in acteurs.values()} - {camp_joueur}
    camp_intermediaire = acteurs.get(controle_intermediaire, {}).get("camp", controle_intermediaire)

    if camp_intermediaire in camps_ennemis:
        return (
            False,
            False,
            f"{intermediaire} est contrôlé par {controle_intermediaire}"
        )

    return True, True, "marche forcee"


def envoyer_general_au_repli(
    joueur,
    nom_general,
    chemin_actuel,
    configuration=None,
    lieu_sanction=None,
    appliquer_sanction=True,
):
    # Envoie le général et toutes ses unités
    # dans sa zone de repli.
    #
    # La fonction refuse d'écraser un général
    # déjà présent dans le repli.

    if configuration is None:
        configuration = config.configuration_mode("classique")
    zone_actuelle = next((zone["position"]
        for acteur in configuration["joueurs"]
        for zone in generaux.zones_generaux(acteur, configuration)
        if zone["chemin"] == chemin_actuel.parent), None)
    if lieu_sanction == "home" or zone_actuelle == "home":
        rapports.afficher_et_ecrire(
            f"Avertissement dans le home : {joueur}:{nom_general}, aucune sanction de repli.")
        return chemin_actuel
    repli = configuration["repli_path"]
    destination = (
        repli
        / joueur
        / nom_general
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Une autre occurrence existe déjà au repli.
    # On ne supprime aucun dossier ici :
    # les fonctions de sécurisation doivent
    # résoudre la duplication auparavant.
    if destination.exists() and chemin_actuel != destination:
        rapports.afficher_et_ecrire(
            f"Impossible d'envoyer "
            f"{joueur}:{nom_general} au repli : "
            f"une occurrence existe déjà."
        )

        return None

    delai = None
    identifiant = f"{joueur}:{nom_general}"
    attentes = etat.charger_attentes_repli(configuration)
    deja_repli = (zone_actuelle == "repli" or lieu_sanction == "repli"
                  or etat.charger_positions_generaux().get(identifiant) == "repli"
                  or identifiant in attentes)
    if appliquer_sanction and not deja_repli:
        delai = delai_sanction_repli(joueur, lieu_sanction or zone_actuelle, configuration)
    elif deja_repli:
        rapports.afficher_et_ecrire(
            f"Anomalie au repli : {identifiant}, délai conservé sans nouvelle sanction.")

    if chemin_actuel != destination:
        shutil.move(str(chemin_actuel), str(destination))

    generaux.donner_permissions_general(
        destination,
        joueur
    )

    if delai is not None:
        attentes[identifiant] = delai
        etat.sauvegarder_attentes_repli(attentes, configuration)
        rapports.afficher_et_ecrire(
            f"Sanction de repli : {joueur}:{nom_general}, {delai} tour(s) d'attente."
        )
    return destination


def destination_retraite_surnombre(origine, configuration):
    """Prochain territoire du plus court chemin vers le village, sans départage."""
    if configuration["mode"] != "survie":
        raise ValueError("La retraite de surnombre exige le profil Survie.")
    villages = configuration["villages"]
    if origine in villages:
        return None
    if len(villages) != 1:
        raise ValueError("Le choix entre plusieurs villages n'est pas défini.")
    tactiques = {territoire.name for territoire in configuration["territoires"]}
    carte = configuration["carte_territoires"]
    distances = {villages[0]: 0}
    attente = deque(villages)
    while attente:
        territoire = attente.popleft()
        for voisin in carte.get(territoire, []):
            if voisin in tactiques and voisin not in distances:
                distances[voisin] = distances[territoire] + 1
                attente.append(voisin)
    candidats = [voisin for voisin in carte.get(origine, [])
                 if voisin in tactiques and voisin in distances
                 and distances[voisin] < distances.get(origine, 0)]
    if not candidats:
        raise ValueError(f"Aucune retraite valide depuis {origine}.")
    minimum = min(distances[voisin] for voisin in candidats)
    meilleurs = [voisin for voisin in candidats if distances[voisin] == minimum]
    if len(meilleurs) != 1:
        raise ValueError("Le départage entre plusieurs routes de retraite reste à définir.")
    return meilleurs[0]


def planifier_positions_surnombre(arrivants, positions_occupees, territoire=None):
    """Calcule tout le placement avant de déplacer un seul général."""
    priorites = []
    cles = set()
    for general in arrivants:
        preference = generaux.lire_fiche_general(general["chemin"]).get("position_surnombre")
        if preference is not None and preference not in {str(n) for n in range(1, 21)}:
            message = (f"Avertissement : position_surnombre invalide pour "
                       f"{general['joueur']}:{general['nom']} ; traité sans préférence.")
            rapports.afficher_et_ecrire(message)
            if territoire is not None:
                rapports.ecrire_rapport_territoire(territoire, message)
            preference = None
        origine = int(general["emplacement"])
        if preference is not None:
            cle = (0, int(preference), origine)
        else:
            cle = (1, 1, origine)
        if cle in cles:
            raise ValueError("Le départage de priorités de surnombre égales reste à définir.")
        cles.add(cle)
        priorites.append((cle, general))
    occupees = {int(place) for place in positions_occupees}
    placements = []
    for (categorie, rang, _), general in sorted(priorites, key=lambda item: item[0]):
        debut = rang if categorie == 0 else 1
        place = next((n for n in range(debut, 21) if n not in occupees), None)
        if place is None:
            message = (f"Avertissement : retraite impossible pour {general['joueur']}:{general['nom']}, "
                       f"aucune place libre entre {debut} et 20 ; reste sur son territoire.")
            rapports.afficher_et_ecrire(message)
            if territoire is not None:
                rapports.ecrire_rapport_territoire(territoire, message)
            continue
        occupees.add(place)
        placements.append((general, str(place)))
    return placements


def retraites_surnombre(arrivants, territoire, configuration):
    """Recule un groupe d'un territoire et le place dans la file alliée.

    Les occupants déjà présents gardent leur place. La réserve est exclue.
    Toutes les destinations sont vérifiées avant le premier déplacement.
    """
    if not arrivants:
        return []
    arrivee = destination_retraite_surnombre(territoire.name, configuration)
    if arrivee is None:
        return [(general, general["chemin"]) for general in arrivants]
    territoire_arrivee = configuration["game_path"] / arrivee
    zones = {joueur: generaux.zones_generaux_territoire(territoire_arrivee, joueur, configuration)
             for joueur in configuration["joueurs"]}
    occupees = set()
    identites = set()
    for joueur, zones_joueur in zones.items():
        for zone in zones_joueur:
            if not zone["chemin"].exists():
                continue
            presents = [p for p in zone["chemin"].iterdir() if p.is_dir()]
            identites.update((joueur, p.name) for p in presents)
            if presents and "emplacement" in zone:
                occupees.add(zone["emplacement"])
    for general in arrivants:
        if general["joueur"] not in configuration["joueurs"]:
            raise ValueError("La retraite de surnombre concerne uniquement les joueurs.")
        identite = (general["joueur"], general["nom"])
        if identite in identites:
            raise FileExistsError(f"Une identité existe déjà à l'arrivée : {identite}")
        identites.add(identite)
    placements = planifier_positions_surnombre(arrivants, occupees, territoire)
    destinations = []
    for general, place in placements:
        zone = next(z for z in zones[general["joueur"]] if z.get("emplacement") == place)
        destination = zone["chemin"] / general["nom"]
        if destination.exists():
            raise FileExistsError(f"Une identité existe déjà à l'arrivée : {destination}")
        if not general["chemin"].is_dir():
            raise FileNotFoundError(general["chemin"])
        destinations.append((general, destination))

    positions = etat.charger_positions_generaux()
    for general, destination in destinations:
        joueur = general["joueur"]
        acteur = configuration["acteurs"][joueur]
        uid = pwd.getpwnam(acteur["proprietaire_linux"]).pw_uid
        gid = grp.getgrnam(acteur["groupe_linux"]).gr_gid
        territoire_arrivee.mkdir(parents=True, exist_ok=True)
        joueur_dir = territoire_arrivee / joueur
        dossiers = [joueur_dir]
        if destination.parent.parent != joueur_dir:
            dossiers.append(destination.parent.parent)
        dossiers.append(destination.parent)
        for dossier in dossiers:
            dossier.mkdir(mode=0o700, exist_ok=True)
            os.chown(dossier, uid, gid)
            os.chmod(dossier, 0o700)
        general["chemin"].rename(destination)
        generaux.donner_permissions_general(destination, acteur["proprietaire_linux"])
        positions[f"{joueur}:{general['nom']}"] = arrivee
        etat.sauvegarder_positions_generaux(positions)
        rapports.afficher_et_ecrire(
            f"Retraite de surnombre : {joueur} {general['nom']} : "
            f"{territoire.name} -> {arrivee}, position {destination.parent.name}."
        )
    return destinations


def retraite_surnombre(general, territoire, configuration):
    """Compatibilité pour la retraite isolée d'un général."""
    destinations = retraites_surnombre([general], territoire, configuration)
    return destinations[0][1] if destinations else general["chemin"]


def ennemi_de(joueur):
    if joueur == "j1":
        return "j2"

    if joueur == "j2":
        return "j1"

    return None
