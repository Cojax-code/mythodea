"""Calcul des combats, choc initial, manœuvres et combat rangé."""
import random
import shutil

import config
import etat
import generaux
import mouvements
import rapports


def combat_entre_generaux(general_1, general_2):
    # Affrontement complet entre deux généraux.
    #
    # Déroulement :
    # 1. Choc initial entre les blocs placés face à face.
    # 2. Manœuvres entre les blocs survivants.

    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    chemin_1 = general_1["chemin"]
    chemin_2 = general_2["chemin"]

    initial_1 = generaux.total_general_depuis_chemin(chemin_1)
    initial_2 = generaux.total_general_depuis_chemin(chemin_2)

    rapports.afficher_et_ecrire(
        f"\nEngagement : "
        f"{joueur_1} {general_1['nom']} VS "
        f"{joueur_2} {general_2['nom']}"
    )

    initiative_avant, details_choc = phase_engagement_initial(
        general_1,
        general_2
    )

    details_manoeuvre = []

    # Le choc initial peut avoir détruit un général.
    if not chemin_1.exists() or not chemin_2.exists():
        return {
            "joueur_1": joueur_1,
            "general_1": general_1["nom"],
            "initial_1": initial_1,
            "final_1": generaux.total_general_depuis_chemin(chemin_1),
            "joueur_2": joueur_2,
            "general_2": general_2["nom"],
            "initial_2": initial_2,
            "final_2": generaux.total_general_depuis_chemin(chemin_2),
            "chocs": details_choc,
            "manoeuvres": details_manoeuvre,
        }

    rapports.afficher_et_ecrire("\n=== MANŒUVRE ===")

    tour = 0
    numero_manoeuvre = 0

    while tour < 10:
        tour += 1

        if not chemin_1.exists() or not chemin_2.exists():
            break

        armee = {
            joueur_1: generaux.lire_blocs_general(chemin_1),
            joueur_2: generaux.lire_blocs_general(chemin_2),
        }

        if (
            generaux.total_unites_general(armee[joueur_1]) == 0
            or generaux.total_unites_general(armee[joueur_2]) == 0
        ):
            break

        rapports.afficher_et_ecrire(f"\n--- Tour de manœuvre {tour} ---")
        attaque_effectuee = False

        actions = ordre_actions_manoeuvre(armee, initiative_avant)
        rapports.afficher_et_ecrire(
            "\nOrdre global de manœuvre : "
            + ", ".join(f"{joueur} {bloc}" for joueur, bloc in actions)
        )

        for joueur_attaquant, bloc_attaquant in actions:
            if not chemin_1.exists() or not chemin_2.exists():
                break

            armee = {
                joueur_1: generaux.lire_blocs_general(chemin_1),
                joueur_2: generaux.lire_blocs_general(chemin_2),
            }

            if generaux.total_unites_general(armee[joueur_1]) == 0:
                break
            if generaux.total_unites_general(armee[joueur_2]) == 0:
                break

            # Les pertes d'une action précédente peuvent avoir détruit ce bloc.
            infos_attaquant = armee[joueur_attaquant][bloc_attaquant]
            if infos_attaquant["nombre"] <= 0:
                continue

            cible = choisir_cible(
                armee,
                joueur_attaquant,
                infos_attaquant["type"]
            )

            if cible is None:
                continue

            if joueur_attaquant == joueur_1:
                general_attaquant = general_1
                general_defenseur = general_2
            else:
                general_attaquant = general_2
                general_defenseur = general_1

            detail = attaque_ciblee(
                armee,
                general_attaquant,
                general_defenseur,
                bloc_attaquant,
                cible
            )

            numero_manoeuvre += 1
            detail["numero"] = numero_manoeuvre
            detail["tour"] = tour
            details_manoeuvre.append(detail)
            attaque_effectuee = True

        if not attaque_effectuee:
            rapports.afficher_et_ecrire(
                "Aucune manœuvre possible. L'affrontement est bloqué."
            )
            break

    if chemin_1.exists():
        generaux.supprimer_general_si_vide(general_1)
    if chemin_2.exists():
        generaux.supprimer_general_si_vide(general_2)

    return {
        "joueur_1": joueur_1,
        "general_1": general_1["nom"],
        "initial_1": initial_1,
        "final_1": generaux.total_general_depuis_chemin(chemin_1),
        "joueur_2": joueur_2,
        "general_2": general_2["nom"],
        "initial_2": initial_2,
        "final_2": generaux.total_general_depuis_chemin(chemin_2),
        "chocs": details_choc,
        "manoeuvres": details_manoeuvre,
    }


def resoudre_attaque_frontale(
    territory,
    mode_combat
):
    # Ordre 1-2 : attaque frontale.
    #
    # Les généraux placés dans les mêmes
    # emplacements s'affrontent d'abord :
    #
    # 1 contre 1
    # 2 contre 2
    # 3 contre 3
    # 4 contre 4
    #
    # Après cette phase, les survivants seront
    # pris en charge par le combat rangé.

    rapports.afficher_et_ecrire(
        "\n=== ORDRE 1-2 : ATTAQUE FRONTALE ==="
    )

    engagement_effectue = False
    resultats = []

    for emplacement in config.emplacements:

        # Relire entièrement le territoire avant
        # chaque duel, car le duel précédent peut
        # avoir supprimé un général.
        generaux_territoire = (
            generaux.lire_generaux_territoire(
                territory
            )
        )

        general_j1 = (
            generaux_territoire[
                "j1"
            ][
                emplacement
            ]
        )

        general_j2 = (
            generaux_territoire[
                "j2"
            ][
                emplacement
            ]
        )

        # Il faut un général actif dans les deux camps
        # au même emplacement.
        if not generaux.general_a_des_unites(
            general_j1
        ):
            rapports.afficher_et_ecrire(
                f"Emplacement {emplacement} : "
                f"aucun général actif pour j1."
            )

            continue

        if not generaux.general_a_des_unites(
            general_j2
        ):
            rapports.afficher_et_ecrire(
                f"Emplacement {emplacement} : "
                f"aucun général actif pour j2."
            )

            continue

        engagement_effectue = True

        rapports.afficher_et_ecrire(
            f"\n--- Duel frontal "
            f"{mode_combat} : "
            f"emplacement {emplacement} ---"
        )

        rapports.afficher_et_ecrire(
            f"{general_j1['nom']} "
            f"contre "
            f"{general_j2['nom']}"
        )

        resultat_duel = combat_entre_generaux(
            general_j1,
            general_j2
        )

        rapports.ecrire_ligne_affrontement_territoire(
            territory,
            emplacement,
            resultat_duel
        )
        resultats.append((emplacement, resultat_duel))

    if not engagement_effectue:
        rapports.afficher_et_ecrire(
            "Ordre 1-2 sans effet : "
            "aucun couple de généraux correspondants."
        )

    return resultats


def resoudre_combat_range(
    territory,
    mode_combat
):
    # Moteur commun de résolution.
    #
    # Première étape éventuelle :
    # - ordre 1-2 : affrontements par emplacement.
    #
    # Deuxième étape :
    # - combat rangé entre les premiers
    #   généraux encore actifs ;
    # - le survivant continue ;
    # - le combat s'arrête lorsqu'un camp disparaît.

    generaux_depart = (
        generaux.lire_generaux_territoire(
            territory
        )
    )

    ordre_frontal_j1 = (
        generaux.joueur_possede_ordre_armee(
            generaux_depart,
            "j1",
            "1-2"
        )
    )

    ordre_frontal_j2 = (
        generaux.joueur_possede_ordre_armee(
            generaux_depart,
            "j2",
            "1-2"
        )
    )

    # Pour cette première version,
    # un seul des deux camps suffit pour provoquer
    # l'organisation frontale du combat.
    if ordre_frontal_j1 or ordre_frontal_j2:

        camps = []

        if ordre_frontal_j1:
            camps.append("j1")

        if ordre_frontal_j2:
            camps.append("j2")

        rapports.afficher_et_ecrire(
            "Ordre frontal demandé par : "
            + ", ".join(camps)
        )

        rapports.ecrire_rapport_territoire(
            territory,
            ""
        )
        rapports.ecrire_rapport_territoire(
            territory,
            "================ ENGAGEMENT FRONTAL ================"
        )
        rapports.ecrire_rapport_territoire(
            territory,
            ""
        )
        rapports.ecrire_entete_tableau_affrontements(
            territory,
            "Pos"
        )

        engagements_frontaux = resoudre_attaque_frontale(
            territory,
            mode_combat
        )

        rapports.ecrire_fin_tableau_affrontements(
            territory
        )

        rapports.ecrire_details_engagements(
            territory,
            engagements_frontaux
        )

    # --------------------------------------------------
    # Combat rangé
    # --------------------------------------------------

    round_combat = 0
    tableau_combat_range_ouvert = False
    engagements_combat_range = []

    while round_combat < 20:
        round_combat += 1

        generaux_territoire = (
            generaux.lire_generaux_territoire(
                territory
            )
        )

        controle = (
            generaux.controle_territoire_generaux(
                generaux_territoire
            )
        )

        if controle != "conteste":
            if tableau_combat_range_ouvert:
                rapports.ecrire_fin_tableau_affrontements(
                    territory
                )
                rapports.ecrire_details_engagements(
                    territory,
                    engagements_combat_range
                )
            else:
                rapports.ecrire_rapport_territoire(territory, "")
                rapports.ecrire_rapport_territoire(
                    territory,
                    "=================== COMBAT RANGÉ ==================="
                )
                rapports.ecrire_rapport_territoire(
                    territory,
                    "Aucun combat rangé."
                )

            rapports.afficher_et_ecrire(
                f"Fin du combat. "
                f"Controle final : {controle}"
            )

            return

        actifs_j1 = generaux.generaux_actifs_joueur(
            generaux_territoire,
            "j1"
        )

        actifs_j2 = generaux.generaux_actifs_joueur(
            generaux_territoire,
            "j2"
        )

        if (
            len(actifs_j1) == 0
            or len(actifs_j2) == 0
        ):
            controle = (
                generaux.controle_territoire_generaux(
                    generaux_territoire
                )
            )

            if tableau_combat_range_ouvert:
                rapports.ecrire_fin_tableau_affrontements(
                    territory
                )
                rapports.ecrire_details_engagements(
                    territory,
                    engagements_combat_range
                )
            else:
                rapports.ecrire_rapport_territoire(territory, "")
                rapports.ecrire_rapport_territoire(
                    territory,
                    "=================== COMBAT RANGÉ ==================="
                )
                rapports.ecrire_rapport_territoire(
                    territory,
                    "Aucun combat rangé."
                )

            rapports.afficher_et_ecrire(
                f"Fin du combat. "
                f"Controle final : {controle}"
            )

            return

        general_j1 = actifs_j1[0]
        general_j2 = actifs_j2[0]

        rapports.afficher_et_ecrire(
            f"\n--- Combat rangé "
            f"{mode_combat} "
            f"{round_combat} ---"
        )

        resultat_combat_range = combat_entre_generaux(
            general_j1,
            general_j2
        )

        if round_combat == 1:
            rapports.ecrire_rapport_territoire(
                territory,
                ""
            )
            rapports.ecrire_rapport_territoire(
                territory,
                "=================== COMBAT RANGÉ ==================="
            )
            rapports.ecrire_rapport_territoire(
                territory,
                ""
            )
            rapports.ecrire_entete_tableau_affrontements(
                territory,
                "Tour"
            )
            tableau_combat_range_ouvert = True

        rapports.ecrire_ligne_affrontement_territoire(
            territory,
            round_combat,
            resultat_combat_range
        )
        engagements_combat_range.append(
            (round_combat, resultat_combat_range)
        )

    if tableau_combat_range_ouvert:
        rapports.ecrire_fin_tableau_affrontements(
            territory
        )
        rapports.ecrire_details_engagements(
            territory,
            engagements_combat_range
        )
    else:
        rapports.ecrire_rapport_territoire(territory, "")
        rapports.ecrire_rapport_territoire(
            territory,
            "=================== COMBAT RANGÉ ==================="
        )
        rapports.ecrire_rapport_territoire(
            territory,
            "Aucun combat rangé."
        )

    generaux_territoire = (
        generaux.lire_generaux_territoire(
            territory
        )
    )

    controle = (
        generaux.controle_territoire_generaux(
            generaux_territoire
        )
    )

    rapports.afficher_et_ecrire(
        f"Limite de rounds atteinte "
        f"sur {territory.name}. "
        f"Controle actuel : {controle}"
    )


def resoudre_combat_v15(territory):
    # Résolution OFF/OFF.

    rapports.afficher_et_ecrire(
        f"\n=== Combat OFF/OFF sur {territory.name} ==="
    )

    resoudre_combat_range(
        territory,
        "OFF/OFF"
    )


def resoudre_combat_off_def(territory, defenseur):
    # Résolution OFF/DEF.
    #
    # Pour l'instant, le moteur de combat est le même que OFF/OFF.
    # Mais on garde la distinction défenseur / attaquant pour les règles futures :
    # terrain, fortification, ravitaillement, avant-poste, brouillard de guerre, etc.

    attaquant = mouvements.ennemi_de(defenseur)

    rapports.afficher_et_ecrire(
        f"\n=== Combat OFF/DEF sur {territory.name} ==="
    )
    rapports.afficher_et_ecrire(
        f"Défenseur : {defenseur} | Attaquant : {attaquant}"
    )

    resoudre_combat_range(territory, "OFF/DEF")


def cible_facile(type_unite):
    if type_unite == "archer":
        return "piquier"

    if type_unite == "piquier":
        return "cavalier"

    if type_unite == "cavalier":
        return "archer"

    return None


def multiplicateur(type_attaquant, type_defenseur):
    if cible_facile(type_attaquant) == type_defenseur:
        return 2

    return 1


def combat_bloc(
    infos_1,
    infos_2,
    fatigue_1=False,
    fatigue_2=False
):
    # Calcule le résultat d'un combat entre deux blocs.
    #
    # Règle de fatigue :
    # si les deux unités sont normalement équivalentes,
    # l'unité non fatiguée obtient l'avantage sur l'unité fatiguée.
    #
    # La fatigue ne modifie pas les avantages naturels
    # entre types différents.

    type_1 = infos_1["type"]
    type_2 = infos_2["type"]

    nombre_1 = infos_1["nombre"]
    nombre_2 = infos_2["nombre"]

    valeur_1 = multiplicateur(
        type_1,
        type_2
    )

    valeur_2 = multiplicateur(
        type_2,
        type_1
    )

    # ------------------------------------------
    # Fatigue
    # ------------------------------------------

    if type_1 == type_2:

        # Général 1 fatigué, général 2 frais.
        if fatigue_1 and not fatigue_2:
            valeur_2 = 2

        # Général 2 fatigué, général 1 frais.
        elif fatigue_2 and not fatigue_1:
            valeur_1 = 2

    degats_1 = nombre_1 * valeur_1
    degats_2 = nombre_2 * valeur_2

    pertes_1 = degats_2 // valeur_1
    pertes_2 = degats_1 // valeur_2

    survivants_1 = max(
        0,
        nombre_1 - pertes_1
    )

    survivants_2 = max(
        0,
        nombre_2 - pertes_2
    )

    return survivants_1, survivants_2


def trouver_cible_facile(armee, joueur_attaquant, type_attaquant):
    joueur_ennemi = mouvements.ennemi_de(joueur_attaquant)
    type_cible = cible_facile(type_attaquant)

    for bloc in config.ordre_blocs:
        infos_ennemi = armee[joueur_ennemi][bloc]

        if infos_ennemi["type"] == type_cible and infos_ennemi["nombre"] > 0:
            return bloc

    return None


def trouver_cible_faible(armee, joueur_ennemi):
    cible = None
    plus_petit_nombre = None

    for bloc in config.ordre_blocs:
        infos = armee[joueur_ennemi][bloc]

        if infos["nombre"] > 0:
            if plus_petit_nombre is None or infos["nombre"] < plus_petit_nombre:
                plus_petit_nombre = infos["nombre"]
                cible = bloc

    return cible


def supprimer_unites(infos, survivants):
    nombre_actuel = infos["nombre"]
    pertes = nombre_actuel - survivants

    unites_supprimees = []

    if pertes <= 0:
        return unites_supprimees

    type_unite = infos["type"]

    unites_a_supprimer = random.sample(infos["unites"], pertes)

    for unite in unites_a_supprimer:
        unites_supprimees.append(f"{unite.name} ({type_unite})")
        shutil.rmtree(unite)

    return unites_supprimees


def confrontation_directe(
    armee,
    general_1,
    general_2,
    bloc
):
    # Résout le choc initial entre deux blocs placés face à face.
    # Retourne aussi les données structurées utilisées par le rapport de bataille.

    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    nom_1 = f"{joueur_1} {general_1['nom']}"
    nom_2 = f"{joueur_2} {general_2['nom']}"

    infos_1 = armee[joueur_1][bloc]
    infos_2 = armee[joueur_2][bloc]

    if infos_1["nombre"] == 0 or infos_2["nombre"] == 0:
        return None

    initial_1 = infos_1["nombre"]
    initial_2 = infos_2["nombre"]
    type_1 = infos_1["type"]
    type_2 = infos_2["type"]

    fatigue_1 = etat.general_est_fatigue(general_1)
    fatigue_2 = etat.general_est_fatigue(general_2)

    rapports.afficher_et_ecrire("\n" + "-" * 60)
    rapports.afficher_et_ecrire(f"Choc initial : {bloc}")
    rapports.afficher_et_ecrire("")

    if fatigue_1:
        rapports.afficher_et_ecrire(f"{nom_1} : FATIGUÉ")

    if fatigue_2:
        rapports.afficher_et_ecrire(f"{nom_2} : FATIGUÉ")

    rapports.afficher_et_ecrire(f"{nom_1} : {rapports.formater_force(infos_1)}")
    rapports.afficher_et_ecrire(f"{nom_2} : {rapports.formater_force(infos_2)}")

    survivants_1, survivants_2 = combat_bloc(
        infos_1,
        infos_2,
        fatigue_1,
        fatigue_2
    )

    rapports.afficher_et_ecrire("\nRésultat :")
    rapports.afficher_et_ecrire(
        f"{nom_1} : {rapports.formater_survivants(survivants_1, type_1)}"
    )
    rapports.afficher_et_ecrire(
        f"{nom_2} : {rapports.formater_survivants(survivants_2, type_2)}"
    )

    pertes_1 = supprimer_unites(infos_1, survivants_1)
    pertes_2 = supprimer_unites(infos_2, survivants_2)

    rapports.afficher_tableau_pertes(pertes_1, pertes_2, nom_1, nom_2)

    return {
        "moment": "Choc",
        "bloc_1": bloc,
        "type_1": type_1,
        "initial_1": initial_1,
        "final_1": survivants_1,
        "bloc_2": bloc,
        "type_2": type_2,
        "initial_2": initial_2,
        "final_2": survivants_2,
    }


def phase_engagement_initial(general_1, general_2):
    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    chemin_1 = general_1["chemin"]
    chemin_2 = general_2["chemin"]

    rapports.afficher_et_ecrire("\n=== CHOC INITIAL ===")

    armee_depart = {
        joueur_1: generaux.lire_blocs_general(chemin_1),
        joueur_2: generaux.lire_blocs_general(chemin_2),
    }

    initiative_avant = {
        joueur_1: False,
        joueur_2: False,
    }

    details_choc = []

    infos_avant_1 = armee_depart[joueur_1]["avant"]
    infos_avant_2 = armee_depart[joueur_2]["avant"]

    if infos_avant_1["nombre"] > 0 and infos_avant_2["nombre"] == 0:
        initiative_avant[joueur_1] = True

    if infos_avant_2["nombre"] > 0 and infos_avant_1["nombre"] == 0:
        initiative_avant[joueur_2] = True

    combats_prevus = []

    for bloc in config.ordre_blocs:
        infos_1 = armee_depart[joueur_1][bloc]
        infos_2 = armee_depart[joueur_2][bloc]

        if infos_1["nombre"] > 0 and infos_2["nombre"] > 0:
            combats_prevus.append(bloc)

    if len(combats_prevus) == 0:
        rapports.afficher_et_ecrire("Aucune confrontation directe prévue.")
        return initiative_avant, details_choc

    rapports.afficher_et_ecrire("\nCombats prévus :")

    for bloc in combats_prevus:
        infos_1 = armee_depart[joueur_1][bloc]
        infos_2 = armee_depart[joueur_2][bloc]

        rapports.afficher_et_ecrire(
            f"- {bloc} : "
            f"{joueur_1} {general_1['nom']} {rapports.formater_force(infos_1)} "
            f"VS "
            f"{joueur_2} {general_2['nom']} {rapports.formater_force(infos_2)}"
        )

    rapports.afficher_et_ecrire("\n--- Résolution du choc initial ---")

    for bloc in combats_prevus:
        if not chemin_1.exists() or not chemin_2.exists():
            break

        armee = {
            joueur_1: generaux.lire_blocs_general(chemin_1),
            joueur_2: generaux.lire_blocs_general(chemin_2),
        }

        detail = confrontation_directe(
            armee,
            general_1,
            general_2,
            bloc
        )

        if detail is not None:
            details_choc.append(detail)

        if chemin_1.exists():
            generaux.supprimer_general_si_vide(general_1)

        if chemin_2.exists():
            generaux.supprimer_general_si_vide(general_2)

    return initiative_avant, details_choc


def attaque_ciblee(
    armee,
    general_attaquant,
    general_defenseur,
    bloc_attaquant,
    bloc_cible
):
    # Résout une manœuvre contre un bloc ennemi.
    # Retourne les données nécessaires au rapport de bataille.

    joueur_attaquant = general_attaquant["joueur"]
    joueur_ennemi = general_defenseur["joueur"]

    nom_attaquant = f"{joueur_attaquant} {general_attaquant['nom']}"
    nom_defenseur = f"{joueur_ennemi} {general_defenseur['nom']}"

    infos_attaquant = armee[joueur_attaquant][bloc_attaquant]
    infos_defenseur = armee[joueur_ennemi][bloc_cible]

    initial_attaquant = infos_attaquant["nombre"]
    initial_defenseur = infos_defenseur["nombre"]
    type_attaquant = infos_attaquant["type"]
    type_defenseur = infos_defenseur["type"]

    fatigue_attaquant = etat.general_est_fatigue(general_attaquant)
    fatigue_defenseur = etat.general_est_fatigue(general_defenseur)

    rapports.afficher_et_ecrire("\n" + "-" * 60)
    rapports.afficher_et_ecrire("Manœuvre")
    rapports.afficher_et_ecrire("")

    rapports.afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} "
        f"attaque {nom_defenseur} {bloc_cible}"
    )

    if fatigue_attaquant:
        rapports.afficher_et_ecrire(f"{nom_attaquant} : FATIGUÉ")

    if fatigue_defenseur:
        rapports.afficher_et_ecrire(f"{nom_defenseur} : FATIGUÉ")

    rapports.afficher_et_ecrire("\nForces engagées :")
    rapports.afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} : {rapports.formater_force(infos_attaquant)}"
    )
    rapports.afficher_et_ecrire(
        f"{nom_defenseur} {bloc_cible} : {rapports.formater_force(infos_defenseur)}"
    )

    survivants_attaquant, survivants_defenseur = combat_bloc(
        infos_attaquant,
        infos_defenseur,
        fatigue_attaquant,
        fatigue_defenseur
    )

    rapports.afficher_et_ecrire("\nRésultat :")
    rapports.afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} : "
        f"{rapports.formater_survivants(survivants_attaquant, type_attaquant)}"
    )
    rapports.afficher_et_ecrire(
        f"{nom_defenseur} {bloc_cible} : "
        f"{rapports.formater_survivants(survivants_defenseur, type_defenseur)}"
    )

    pertes_attaquant = supprimer_unites(
        infos_attaquant,
        survivants_attaquant
    )
    pertes_defenseur = supprimer_unites(
        infos_defenseur,
        survivants_defenseur
    )

    rapports.afficher_tableau_pertes(
        pertes_attaquant,
        pertes_defenseur,
        nom_attaquant,
        nom_defenseur
    )

    return {
        "joueur_attaquant": joueur_attaquant,
        "bloc_attaquant": bloc_attaquant,
        "type_attaquant": type_attaquant,
        "initial_attaquant": initial_attaquant,
        "final_attaquant": survivants_attaquant,
        "joueur_defenseur": joueur_ennemi,
        "bloc_defenseur": bloc_cible,
        "type_defenseur": type_defenseur,
        "initial_defenseur": initial_defenseur,
        "final_defenseur": survivants_defenseur,
    }


def choisir_flanc_attaquant(armee, joueur):
    # Choisit le flanc qui doit agir en premier.
    #
    # Règles :
    # - le flanc le plus nombreux agit en premier ;
    # - en cas d'égalité, le choix est aléatoire ;
    # - si les deux flancs sont vides, retourne None.

    nombre_droite = armee[joueur]["droite"]["nombre"]
    nombre_gauche = armee[joueur]["gauche"]["nombre"]

    if nombre_droite == 0 and nombre_gauche == 0:
        return None

    if nombre_droite > nombre_gauche:
        return "droite"

    if nombre_gauche > nombre_droite:
        return "gauche"

    return random.choice(["droite", "gauche"])


def choisir_cible(armee, joueur_attaquant, type_attaquant):
    joueur_ennemi = mouvements.ennemi_de(joueur_attaquant)

    cible = trouver_cible_facile(armee, joueur_attaquant, type_attaquant)

    if cible is None:
        cible = trouver_cible_faible(armee, joueur_ennemi)

    return cible


def ordre_attaques_initiative(armee, joueur, initiative_avant):
    # Ordre :
    # 1. avant-garde si elle n'a pas été engagée en phase 1
    # 2. arrière-garde
    # 3. flanc le plus nombreux
    # 4. second flanc
    # 5. avant-garde si elle n'a pas déjà agi

    ordre = []
    avant_deja_ajoute = False

    if (
        initiative_avant[joueur]
        and armee[joueur]["avant"]["nombre"] > 0
    ):
        ordre.append("avant")
        avant_deja_ajoute = True

    if armee[joueur]["arriere"]["nombre"] > 0:
        ordre.append("arriere")

    premier_flanc = choisir_flanc_attaquant(armee, joueur)

    if premier_flanc is not None:
        ordre.append(premier_flanc)

        if premier_flanc == "droite":
            second_flanc = "gauche"
        else:
            second_flanc = "droite"

        if armee[joueur][second_flanc]["nombre"] > 0:
            ordre.append(second_flanc)

    if (
        not avant_deja_ajoute
        and armee[joueur]["avant"]["nombre"] > 0
    ):
        ordre.append("avant")

    return ordre


def ordre_actions_manoeuvre(armee, initiative_avant):
    # Réunit les deux camps par priorité de bloc, sans tour réservé à un joueur.
    # Après le choc, les blocs survivants n'ont plus de vis-à-vis direct :
    # il ne reste au plus qu'un arrière et un avant (libre ou engagé).
    priorites = [[], [], [], []]

    for joueur in armee:
        for bloc in ordre_attaques_initiative(armee, joueur, initiative_avant):
            if bloc == "avant":
                rang = 0 if initiative_avant[joueur] else 3
            elif bloc == "arriere":
                rang = 1
            else:
                rang = 2
            priorites[rang].append((joueur, bloc))

    # Le tri stable après mélange départage seulement les flancs égaux au hasard.
    flancs = priorites[2]
    if len(flancs) > 1:
        random.shuffle(flancs)
        flancs.sort(key=lambda action: -armee[action[0]][action[1]]["nombre"])

    return [action for groupe in priorites for action in groupe]
