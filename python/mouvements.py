"""Règles de déplacement, marche forcée et envoi au repli."""
import shutil

import config
import generaux
import rapports


def territoires_adjacents(territoire_depart, territoire_arrivee):
    voisins = config.carte_territoires.get(territoire_depart, [])
    return territoire_arrivee in voisins


def chemin_deux_territoires(
    origine,
    destination
):
    # Cherche un territoire intermédiaire permettant :
    # origine -> intermédiaire -> destination.

    for intermediaire in config.carte_territoires.get(
        origine,
        []
    ):
        if destination in config.carte_territoires.get(
            intermediaire,
            []
        ):
            return intermediaire

    return None


def verifier_deplacement_general(
    joueur,
    origine,
    destination,
    controle_avant
):
    base = config.bases_joueurs[joueur]

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
    if destination in config.carte_territoires.get(
        origine,
        []
    ):
        return True, False, "deplacement normal"

    # Marche forcée : 2 territoires.
    intermediaire = chemin_deux_territoires(
        origine,
        destination
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

    joueur_ennemi = ennemi_de(joueur)

    if controle_intermediaire == joueur_ennemi:
        return (
            False,
            False,
            f"{intermediaire} est contrôlé par {joueur_ennemi}"
        )

    return True, True, "marche forcee"


def envoyer_general_au_repli(
    joueur,
    nom_general,
    chemin_actuel
):
    # Envoie le général et toutes ses unités
    # dans sa zone de repli.
    #
    # La fonction refuse d'écraser un général
    # déjà présent dans le repli.

    destination = (
        config.repli_path
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


def ennemi_de(joueur):
    if joueur == "j1":
        return "j2"

    if joueur == "j2":
        return "j1"

    return None
