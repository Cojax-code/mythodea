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
    configuration=None
):
    # Envoie le général et toutes ses unités
    # dans sa zone de repli.
    #
    # La fonction refuse d'écraser un général
    # déjà présent dans le repli.

    repli = config.repli_path if configuration is None else configuration["repli_path"]
    destination = (
        repli
        / joueur
        / nom_general
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Le général est déjà au repli.
    if chemin_actuel == destination:
        generaux.donner_permissions_general(
            destination,
            joueur
        )

        return destination

    # Une autre occurrence existe déjà au repli.
    # On ne supprime aucun dossier ici :
    # les fonctions de sécurisation doivent
    # résoudre la duplication auparavant.
    if destination.exists():
        rapports.afficher_et_ecrire(
            f"Impossible d'envoyer "
            f"{joueur}:{nom_general} au repli : "
            f"une occurrence existe déjà."
        )

        return None

    shutil.move(
        str(chemin_actuel),
        str(destination)
    )

    generaux.donner_permissions_general(
        destination,
        joueur
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


def retraite_surnombre(general, territoire, configuration):
    """Déplace le général vers le village en conservant son numéro de place.

    L'orchestrateur applique ensuite l'audit commun des collisions à l'arrivée.
    Le choix de surnombre et la fatigue restent attachés au général.
    """
    joueur = general["joueur"]
    if joueur not in configuration["joueurs"]:
        raise ValueError("La retraite de surnombre concerne uniquement les joueurs.")
    arrivee = destination_retraite_surnombre(territoire.name, configuration)
    if arrivee is None:
        return general["chemin"]
    territoire_arrivee = configuration["game_path"] / arrivee
    zone = next(z for z in generaux.zones_generaux_territoire(
        territoire_arrivee, joueur, configuration)
        if z.get("emplacement") == general["emplacement"])
    destination = zone["chemin"] / general["nom"]
    if destination.exists():
        raise FileExistsError(f"Une identité existe déjà à l'arrivée : {destination}")
    acteur = configuration["acteurs"][joueur]
    uid = pwd.getpwnam(acteur["proprietaire_linux"]).pw_uid
    gid = grp.getgrnam(acteur["groupe_linux"]).gr_gid
    territoire_arrivee.mkdir(parents=True, exist_ok=True)
    dossiers = [territoire_arrivee / joueur]
    if zone["chemin"].parent != dossiers[0]:
        dossiers.append(zone["chemin"].parent)
    dossiers.append(zone["chemin"])
    for dossier in dossiers:
        dossier.mkdir(mode=0o700, exist_ok=True)
        os.chown(dossier, uid, gid)
        os.chmod(dossier, 0o700)
    general["chemin"].rename(destination)
    generaux.donner_permissions_general(destination, acteur["proprietaire_linux"])
    positions = etat.charger_positions_generaux()
    positions[f"{joueur}:{general['nom']}"] = arrivee
    etat.sauvegarder_positions_generaux(positions)
    rapports.afficher_et_ecrire(
        f"Retraite de surnombre : {joueur} {general['nom']} : {territoire.name} -> {arrivee}."
    )
    return destination


def ennemi_de(joueur):
    if joueur == "j1":
        return "j2"

    if joueur == "j2":
        return "j1"

    return None
