"""Audit des généraux et validation des actions avant les combats."""
from pathlib import Path
import pwd
import shutil

import config
import etat
import generaux
import mouvements
import rapports


def joueur_proprietaire_chemin(chemin):
    # Retrouve le joueur propriétaire d'un dossier
    # à partir de son UID Linux.
    #
    # Retourne :
    # "j1", "j2" ou None si le propriétaire
    # ne correspond à aucun joueur connu.

    try:
        uid_chemin = chemin.stat().st_uid
    except FileNotFoundError:
        return None

    for joueur in config.joueurs:
        uid_joueur = pwd.getpwnam(joueur).pw_uid

        if uid_chemin == uid_joueur:
            return joueur

    return None


def securiser_generaux_mauvais_joueur(
    positions_avant
):
    # Vérifie qu'un général se trouve bien dans
    # l'arborescence de son véritable propriétaire.
    #
    # L'identité du propriétaire est déterminée
    # grâce à l'UID Linux du dossier.
    #
    # Exemple interdit :
    # un dossier appartenant à j1 placé dans :
    # terrain2/j2/1/general1
    #
    # La fonction retourne les identifiants punis.

    generaux_punis = set()

    for joueur_zone in config.joueurs:

        zones = [
            (
                "home",
                Path(f"/home/{joueur_zone}")
            ),
            (
                "repli",
                config.repli_path / joueur_zone
            ),
        ]

        for territory in config.territoires:
            for emplacement in config.emplacements:
                zones.append(
                    (
                        territory.name,
                        territory
                        / joueur_zone
                        / emplacement
                    )
                )

        for nom_zone, chemin_zone in zones:

            if not chemin_zone.exists():
                continue

            for chemin_general in list(
                chemin_zone.iterdir()
            ):
                if not chemin_general.is_dir():
                    continue

                numero = generaux.numero_general_depuis_nom(
                    chemin_general.name
                )

                if numero is None:
                    continue

                proprietaire_reel = (
                    joueur_proprietaire_chemin(
                        chemin_general
                    )
                )

                # Le propriétaire est correct.
                if proprietaire_reel == joueur_zone:
                    continue

                # Propriétaire Linux inconnu :
                # le dossier ne peut pas être considéré
                # comme un véritable général.
                if proprietaire_reel is None:
                    rapports.afficher_et_ecrire(
                        f"Général au propriétaire inconnu "
                        f"supprimé : "
                        f"{chemin_general}"
                    )

                    shutil.rmtree(
                        chemin_general
                    )

                    continue

                identifiant = (
                    f"{proprietaire_reel}:"
                    f"{chemin_general.name}"
                )

                rapports.afficher_et_ecrire(
                    f"{identifiant} placé dans "
                    f"l'arborescence de {joueur_zone} "
                    f"({nom_zone})."
                )

                dernier_numero = etat.lire_compteur_general(
                    proprietaire_reel
                )

                # Le dossier appartient bien à un joueur,
                # mais le général n'est pas officiellement actif.
                if (
                    numero < 1
                    or numero > dernier_numero
                    or identifiant not in positions_avant
                ):
                    rapports.afficher_et_ecrire(
                        f"Général non autorisé supprimé : "
                        f"{identifiant}"
                    )

                    shutil.rmtree(
                        chemin_general
                    )

                    continue

                occurrences_correctes = (
                    generaux.trouver_toutes_positions_general(
                        proprietaire_reel,
                        chemin_general.name
                    )
                )

                # --------------------------------------
                # Aucune autre occurrence
                # --------------------------------------

                if len(occurrences_correctes) == 0:
                    destination = (
                        config.repli_path
                        / proprietaire_reel
                        / chemin_general.name
                    )

                    destination.parent.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    # Il ne devrait normalement pas déjà
                    # exister de destination puisque
                    # occurrences_correctes est vide.
                    if destination.exists():
                        shutil.rmtree(
                            destination
                        )

                    shutil.move(
                        str(chemin_general),
                        str(destination)
                    )

                    generaux.donner_permissions_general(
                        destination,
                        proprietaire_reel
                    )

                    generaux_punis.add(
                        identifiant
                    )

                    rapports.afficher_et_ecrire(
                        f"{identifiant} envoyé au repli "
                        f"de {proprietaire_reel}."
                    )

                    continue

                # --------------------------------------
                # Une occurrence correcte existe déjà
                # --------------------------------------

                shutil.rmtree(
                    chemin_general
                )

                rapports.afficher_et_ecrire(
                    f"Copie située chez {joueur_zone} "
                    f"supprimée : {identifiant}"
                )

                # S'il n'existe qu'une occurrence correcte,
                # elle reçoit immédiatement la sanction.
                #
                # S'il y en a plusieurs, la fonction
                # securiser_generaux_dupliques()
                # traitera ensuite la duplication.
                if len(occurrences_correctes) == 1:
                    occurrence_reelle = (
                        occurrences_correctes[0]
                    )

                    if (
                        occurrence_reelle["position"]
                        != "repli"
                    ):
                        mouvements.envoyer_general_au_repli(
                            proprietaire_reel,
                            chemin_general.name,
                            occurrence_reelle["chemin"]
                        )

                    generaux_punis.add(
                        identifiant
                    )

                    rapports.afficher_et_ecrire(
                        f"{identifiant} envoyé au repli "
                        f"pour placement chez "
                        f"{joueur_zone}."
                    )

    return generaux_punis


def supprimer_generaux_non_autorises():
    # Supprime les dossiers generalX qui ne correspondent
    # à aucun général généré et encore officiellement actif.

    positions = etat.charger_positions_generaux()

    for joueur in config.joueurs:
        dernier_numero = etat.lire_compteur_general(joueur)

        # ------------------------------------------
        # Home
        # ------------------------------------------

        zones_a_verifier = [
            Path(f"/home/{joueur}"),
            config.repli_path / joueur,
        ]

        for zone in zones_a_verifier:

            if not zone.exists():
                continue

            for element in list(zone.iterdir()):

                if not element.is_dir():
                    continue

                if not element.name.startswith("general"):
                    continue

                numero = generaux.numero_general_depuis_nom(
                    element.name
                )

                if (
                    numero is None
                    or numero < 1
                    or numero > dernier_numero
                    or f"{joueur}:{element.name}" not in positions
                ):
                    rapports.afficher_et_ecrire(
                        f"Général non autorisé supprimé : "
                        f"{joueur} {element.name}"
                    )

                    shutil.rmtree(element)

        # ------------------------------------------
        # Territoires
        # ------------------------------------------

        for territory in config.territoires:
            for emplacement in config.emplacements:

                emplacement_dir = (
                    territory
                    / joueur
                    / emplacement
                )

                if not emplacement_dir.exists():
                    continue

                for element in list(
                    emplacement_dir.iterdir()
                ):

                    if not element.is_dir():
                        continue

                    if not element.name.startswith(
                        "general"
                    ):
                        continue

                    numero = generaux.numero_general_depuis_nom(
                        element.name
                    )

                    if (
                        numero is None
                        or numero < 1
                        or numero > dernier_numero
                        or f"{joueur}:{element.name}" not in positions
                    ):
                        rapports.afficher_et_ecrire(
                            f"Général non autorisé supprimé : "
                            f"{joueur} {element.name} "
                            f"sur {territory.name}"
                        )

                        shutil.rmtree(element)


def securiser_generaux_dupliques(positions_avant):
    # Détecte les généraux présents plusieurs fois.
    #
    # En cas de duplication :
    # - une seule copie est conservée ;
    # - les autres sont supprimées ;
    # - la copie conservée est envoyée au repli.
    #
    # La fonction retourne les identifiants punis.

    generaux_punis = set()

    for joueur in config.joueurs:
        dernier_numero = etat.lire_compteur_general(joueur)

        for numero in range(
            1,
            dernier_numero + 1
        ):
            nom_general = f"general{numero}"
            identifiant = (
                f"{joueur}:{nom_general}"
            )

            occurrences = (
                generaux.trouver_toutes_positions_general(
                    joueur,
                    nom_general
                )
            )

            if len(occurrences) <= 1:
                continue

            rapports.afficher_et_ecrire(
                f"{identifiant} est présent "
                f"{len(occurrences)} fois."
            )

            ancienne_position = (
                positions_avant.get(identifiant)
            )

            copie_a_garder = None

            # Si possible, conserver la copie située
            # à la position officielle du tour précédent.
            for occurrence in occurrences:

                if (
                    occurrence["position"]
                    == ancienne_position
                ):
                    copie_a_garder = occurrence
                    break

            # Si aucune copie n'est à l'ancienne position,
            # on en choisit une de manière déterministe.
            if copie_a_garder is None:
                occurrences = sorted(
                    occurrences,
                    key=lambda x: str(x["chemin"])
                )

                copie_a_garder = occurrences[0]

            # Supprimer toutes les autres copies.
            for occurrence in occurrences:

                if occurrence is copie_a_garder:
                    continue

                chemin = occurrence["chemin"]

                if chemin.exists():
                    shutil.rmtree(chemin)

                    rapports.afficher_et_ecrire(
                        f"Copie illégale supprimée : "
                        f"{identifiant} "
                        f"({occurrence['position']})"
                    )

            # La copie réelle reçoit malgré tout
            # la sanction de repli.
            chemin_garde = (
                copie_a_garder["chemin"]
            )

            if (
                copie_a_garder["position"]
                != "repli"
            ):
                mouvements.envoyer_general_au_repli(
                    joueur,
                    nom_general,
                    chemin_garde
                )

            generaux_punis.add(
                identifiant
            )

            rapports.afficher_et_ecrire(
                f"{identifiant} envoyé au repli "
                f"pour duplication."
            )

    return generaux_punis


def securiser_emplacements_generaux():
    # Un emplacement ne peut contenir qu'un général.
    #
    # Si plusieurs généraux sont placés dans le même
    # emplacement, tous sont envoyés au repli.
    #
    # Cela empêche de choisir arbitrairement lequel
    # serait autorisé à rester.

    generaux_punis = set()

    for territory in config.territoires:
        for joueur in config.joueurs:
            for emplacement in config.emplacements:

                emplacement_dir = (
                    territory
                    / joueur
                    / emplacement
                )

                if not emplacement_dir.exists():
                    continue

                generaux_trouves = []

                for element in (
                    emplacement_dir.iterdir()
                ):
                    if (
                        element.is_dir()
                        and element.name.startswith(
                            "general"
                        )
                    ):
                        generaux_trouves.append(
                            element
                        )

                if len(generaux_trouves) <= 1:
                    continue

                rapports.afficher_et_ecrire(
                    f"Emplacement invalide : "
                    f"{territory.name} "
                    f"{joueur}/{emplacement} "
                    f"contient plusieurs généraux."
                )

                for chemin_general in (
                    generaux_trouves
                ):
                    identifiant = (
                        f"{joueur}:"
                        f"{chemin_general.name}"
                    )

                    mouvements.envoyer_general_au_repli(
                        joueur,
                        chemin_general.name,
                        chemin_general
                    )

                    generaux_punis.add(
                        identifiant
                    )

                    rapports.afficher_et_ecrire(
                        f"{identifiant} envoyé "
                        f"au repli."
                    )

    return generaux_punis


def verifier_tous_les_deplacements():
    # Vérifie et sécurise tous les déplacements
    # avant la résolution des combats.
    #
    # Ordre :
    # 1. détecter les généraux placés chez
    #    le mauvais joueur ;
    # 2. supprimer les faux généraux ;
    # 3. détecter les duplications ;
    # 4. détecter les conflits d'emplacement ;
    # 5. vérifier les déplacements ;
    # 6. enregistrer les marches forcées.

    rapports.afficher_et_ecrire(
        "\n=== Vérification des déplacements ==="
    )

    positions = etat.charger_positions_generaux()
    controle_avant = etat.charger_controle_territoires()

    # ------------------------------------------
    # Sécurité générale
    # ------------------------------------------

    punis_mauvais_joueur = (
        securiser_generaux_mauvais_joueur(
            positions
        )
    )

    supprimer_generaux_non_autorises()

    punis_duplication = (
        securiser_generaux_dupliques(
            positions
        )
    )

    punis_emplacement = (
        securiser_emplacements_generaux()
    )

    generaux_deja_punis = (
        punis_mauvais_joueur
        | punis_duplication
        | punis_emplacement
    )

    # ------------------------------------------
    # Fatigue du nouveau tour
    # ------------------------------------------

    generaux_fatigues = set()
    nouvelles_positions = {}

    # ------------------------------------------
    # Vérification individuelle
    # ------------------------------------------

    for joueur in config.joueurs:
        dernier_numero = (
            etat.lire_compteur_general(joueur)
        )

        for numero in range(
            1,
            dernier_numero + 1
        ):
            nom_general = f"general{numero}"

            identifiant = (
                f"{joueur}:{nom_general}"
            )

            position_actuelle, chemin_actuel = (
                generaux.trouver_position_general(
                    joueur,
                    nom_general
                )
            )

            # Général détruit ou absent.
            if position_actuelle is None:
                continue

            # Un général sanctionné pendant l'audit
            # doit maintenant se trouver au repli.
            if identifiant in generaux_deja_punis:
                nouvelles_positions[
                    identifiant
                ] = "repli"

                continue

            origine = positions.get(
                identifiant
            )

            # Aucun enregistrement implicite : seul le moteur peut
            # autoriser une nouvelle identité lors de sa génération.
            if origine is None:
                shutil.rmtree(chemin_actuel)
                rapports.afficher_et_ecrire(
                    f"Général sans position officielle supprimé : {identifiant}"
                )

                continue

            autorise, fatigue, raison = (
                mouvements.verifier_deplacement_general(
                    joueur,
                    origine,
                    position_actuelle,
                    controle_avant
                )
            )

            # --------------------------------------
            # Mouvement valide
            # --------------------------------------

            if autorise:
                nouvelles_positions[
                    identifiant
                ] = position_actuelle

                if fatigue:
                    generaux_fatigues.add(
                        identifiant
                    )

                    rapports.afficher_et_ecrire(
                        f"{identifiant} : "
                        f"{origine} -> "
                        f"{position_actuelle} "
                        f"[MARCHE FORCÉE - FATIGUE]"
                    )

                elif origine == position_actuelle:
                    rapports.afficher_et_ecrire(
                        f"{identifiant} : "
                        f"reste sur {origine}"
                    )

                else:
                    rapports.afficher_et_ecrire(
                        f"{identifiant} : "
                        f"{origine} -> "
                        f"{position_actuelle} "
                        f"[{raison}]"
                    )

                continue

            # --------------------------------------
            # Mouvement interdit
            # --------------------------------------

            rapports.afficher_et_ecrire(
                f"{identifiant} : "
                f"déplacement interdit "
                f"{origine} -> "
                f"{position_actuelle}"
            )

            rapports.afficher_et_ecrire(
                f"Raison : {raison}"
            )

            mouvements.envoyer_general_au_repli(
                joueur,
                nom_general,
                chemin_actuel
            )

            nouvelles_positions[
                identifiant
            ] = "repli"

            rapports.afficher_et_ecrire(
                f"{identifiant} envoyé au repli."
            )

    # ------------------------------------------
    # Sauvegarde
    # ------------------------------------------

    etat.sauvegarder_positions_generaux(
        nouvelles_positions
    )

    etat.sauvegarder_generaux_fatigues(
        generaux_fatigues
    )
