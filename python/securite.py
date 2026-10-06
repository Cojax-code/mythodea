"""Audit des généraux et validation des actions avant les combats."""
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
    positions_avant, configuration=None
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

    if configuration is None:
        configuration = config.configuration_mode("classique")
    generaux_punis = set()

    for joueur_zone in configuration["joueurs"]:
        for zone in generaux.zones_generaux(joueur_zone, configuration):
            nom_zone = zone["position"]
            chemin_zone = zone["chemin"]

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
                        chemin_general.name,
                        configuration
                    )
                )

                # --------------------------------------
                # Aucune autre occurrence
                # --------------------------------------

                if len(occurrences_correctes) == 0:
                    mouvements.envoyer_general_au_repli(
                        proprietaire_reel, chemin_general.name, chemin_general,
                        configuration, lieu_sanction=nom_zone)

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

                # Vérifier la durée avant de supprimer la copie : home/repli
                # ne possèdent pas encore de distance de sanction définie.
                mouvements.delai_sanction_repli(proprietaire_reel, nom_zone, configuration)
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

                    mouvements.envoyer_general_au_repli(
                        proprietaire_reel,
                        chemin_general.name,
                        occurrence_reelle["chemin"],
                        configuration,
                        lieu_sanction=nom_zone,
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


def supprimer_generaux_non_autorises(configuration=None):
    # Même contrôle d'identité dans toutes les zones, y compris les réserves.
    if configuration is None:
        configuration = config.configuration_mode("classique")
    positions = etat.charger_positions_generaux()
    for joueur in configuration["joueurs"]:
        dernier_numero = etat.lire_compteur_general(joueur)
        for zone in generaux.zones_generaux(joueur, configuration):
            chemin = zone["chemin"]
            if not chemin.exists():
                continue
            for element in list(chemin.iterdir()):
                if not element.is_dir() or not element.name.startswith("general"):
                    continue
                numero = generaux.numero_general_depuis_nom(element.name)
                if (numero is None or numero < 1 or numero > dernier_numero
                        or f"{joueur}:{element.name}" not in positions):
                    suffixe = ""
                    if zone["position"] not in ("home", "repli"):
                        suffixe = f" sur {zone['position']}"
                    rapports.afficher_et_ecrire(
                        f"Général non autorisé supprimé : {joueur} {element.name}{suffixe}"
                    )
                    shutil.rmtree(element)


def securiser_generaux_dupliques(positions_avant, configuration=None):
    # Détecte les généraux présents plusieurs fois.
    #
    # En cas de duplication :
    # - une seule copie est conservée ;
    # - les autres sont supprimées ;
    # - la copie conservée est envoyée au repli.
    #
    # La fonction retourne les identifiants punis.

    if configuration is None:
        configuration = config.configuration_mode("classique")
    generaux_punis = set()

    for joueur in configuration["joueurs"]:
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
                    nom_general,
                    configuration
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

            # Valider le délai avant les suppressions ; une zone spéciale
            # sans règle de distance doit être signalée sans perte de dossiers.
            if copie_a_garder["position"] != "repli":
                mouvements.delai_sanction_repli(joueur, copie_a_garder["position"], configuration)

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
                    chemin_garde,
                    configuration
                )

            generaux_punis.add(
                identifiant
            )

            rapports.afficher_et_ecrire(
                f"{identifiant} envoyé au repli "
                f"pour duplication."
            )

    return generaux_punis


def securiser_emplacements_generaux(configuration=None, territoire=None):
    """Sanctionne tous les occupants d'une position en collision.

    En classique, les positions sont propres à chaque joueur. En Survie,
    elles sont communes aux joueurs du même camp. La réserve est exclue.
    """
    if configuration is None:
        configuration = config.configuration_mode("classique")
    generaux_punis = set()
    territoires = configuration["territoires"] if territoire is None else [territoire]
    for territory in territoires:
        positions = {}
        for joueur in configuration["joueurs"]:
            camp = configuration["acteurs"][joueur]["camp"]
            groupe = camp if configuration["emplacements_partages"] else joueur
            for zone in generaux.zones_generaux_territoire(territory, joueur, configuration):
                if "emplacement" not in zone or not zone["chemin"].exists():
                    continue
                cle = (groupe, zone["emplacement"])
                occupants = positions.setdefault(cle, [])
                for element in zone["chemin"].iterdir():
                    if element.is_dir() and element.name.startswith("general"):
                        occupants.append((joueur, element))

        for (groupe, emplacement), occupants in positions.items():
            if len(occupants) <= 1:
                continue
            rapports.afficher_et_ecrire(
                f"Emplacement invalide : {territory.name} "
                f"{groupe}/{emplacement} contient plusieurs généraux."
            )
            for joueur, chemin_general in occupants:
                identifiant = f"{joueur}:{chemin_general.name}"
                mouvements.envoyer_general_au_repli(
                    joueur, chemin_general.name, chemin_general, configuration
                )
                generaux_punis.add(identifiant)
                rapports.afficher_et_ecrire(f"{identifiant} envoyé au repli.")
    return generaux_punis


def verifier_tous_les_deplacements(configuration=None):
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

    if configuration is None:
        configuration = config.configuration_mode("classique")

    rapports.afficher_et_ecrire(
        "\n=== Vérification des déplacements ==="
    )

    positions = etat.charger_positions_generaux()
    controle_avant = etat.charger_controle_territoires(configuration)
    attentes_avant = etat.charger_attentes_repli(configuration)

    # ------------------------------------------
    # Sécurité générale
    # ------------------------------------------

    punis_mauvais_joueur = (
        securiser_generaux_mauvais_joueur(
            positions, configuration
        )
    )

    supprimer_generaux_non_autorises(configuration)

    punis_duplication = (
        securiser_generaux_dupliques(
            positions, configuration
        )
    )

    # Un général encore en attente ne peut pas entrer en combat ni occuper
    # une place alliée. Le retour forcé n'ajoute pas une nouvelle sanction.
    for identifiant in attentes_avant:
        if identifiant in punis_mauvais_joueur | punis_duplication:
            continue
        joueur, nom = identifiant.split(":", 1)
        if joueur not in configuration["joueurs"]:
            continue
        position, chemin = generaux.trouver_position_general(joueur, nom, configuration)
        if chemin is not None and position != "repli":
            mouvements.envoyer_general_au_repli(
                joueur, nom, chemin, configuration, appliquer_sanction=False)
        if chemin is not None:
            rapports.afficher_et_ecrire(
                f"{identifiant} : action interdite, attente au repli "
                f"({attentes_avant[identifiant]} tour(s)).")

    punis_emplacement = (
        securiser_emplacements_generaux(configuration)
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
    # Les acteurs pilotés par le moteur ne sont pas audités comme des joueurs.
    acteurs_automatiques = set(configuration["acteurs"]) - set(configuration["joueurs"])
    nouvelles_positions = {
        identifiant: position for identifiant, position in positions.items()
        if identifiant.split(":", 1)[0] in acteurs_automatiques
    }

    # ------------------------------------------
    # Vérification individuelle
    # ------------------------------------------

    for joueur in configuration["joueurs"]:
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
                    nom_general,
                    configuration
                )
            )

            # Général détruit ou absent.
            if position_actuelle is None:
                continue

            # Un général sanctionné pendant l'audit
            # doit maintenant se trouver au repli.
            if identifiant in generaux_deja_punis or identifiant in attentes_avant:
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
                    controle_avant,
                    configuration
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
                chemin_actuel,
                configuration
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
    # Un appel d'audit valide les actions d'un tour. Seuls les délais déjà
    # présents à son début diminuent ; une sanction nouvelle garde sa durée.
    attentes = etat.charger_attentes_repli(configuration)
    for identifiant in attentes_avant:
        if identifiant not in nouvelles_positions:
            attentes.pop(identifiant, None)
        elif identifiant not in generaux_deja_punis:
            attentes[identifiant] = max(0, attentes_avant[identifiant] - 1)
    if attentes or attentes_avant:
        etat.sauvegarder_attentes_repli(attentes, configuration)
    generaux.scanner_ordres_surnombre(configuration)
