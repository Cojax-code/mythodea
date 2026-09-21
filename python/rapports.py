"""Écriture, formatage et affichage des rapports du tour."""
from pathlib import Path

import config
import etat


territoire_rapport_actuel = None
meteo_tour = None


def formater_force(infos):
    # Transforme les informations d'un bloc en texte lisible.
    #
    # Exemples :
    # 0 unité  → "aucune unité"
    # 1 archer → "1 archer"
    # 4 archer → "4 archers"

    nombre = infos["nombre"]
    type_unite = infos["type"]

    if nombre <= 0:
        return "aucune unité"

    if nombre == 1:
        return f"1 {type_unite}"

    return f"{nombre} {type_unite}s"


def formater_survivants(nombre, type_unite):
    # Présente le résultat d'un bloc après le combat.

    if nombre <= 0:
        return "aucune unité survivante"

    if nombre == 1:
        return f"1 {type_unite} survivant"

    return f"{nombre} {type_unite}s survivants"


def afficher_tableau_pertes(pertes_joueur_1, pertes_joueur_2, nom_joueur_1, nom_joueur_2):
    if len(pertes_joueur_1) == 0 and len(pertes_joueur_2) == 0:
        afficher_et_ecrire("Aucune perte.")
        return

    afficher_et_ecrire("\nPertes :")
    afficher_et_ecrire(f"{nom_joueur_1:<35} | {nom_joueur_2:<35}")
    afficher_et_ecrire("-" * 35 + "-+-" + "-" * 35)

    longueur = max(len(pertes_joueur_1), len(pertes_joueur_2))

    for i in range(longueur):
        if i < len(pertes_joueur_1):
            gauche = pertes_joueur_1[i]
        else:
            gauche = ""

        if i < len(pertes_joueur_2):
            droite = pertes_joueur_2[i]
        else:
            droite = ""

        afficher_et_ecrire(f"{gauche:<35} | {droite:<35}")


def ajouter_ligne_fichier(chemin, texte):
    # Ajoute une ligne dans un fichier de rapport.

    chemin.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        chemin,
        "a",
        encoding="utf-8"
    ) as fichier:
        fichier.write(
            str(texte) + "\n"
        )


def ecrire_rapport_long(texte):
    # Rapport complet réservé au développement,
    # aux tests et au futur système de renseignement.

    ajouter_ligne_fichier(
        config.rapport_long_path,
        texte
    )


def ecrire_rapport_court(texte):
    # Rapport contenant uniquement
    # les informations publiques.

    ajouter_ligne_fichier(
        config.rapport_court_path,
        texte
    )


def chemin_rapport_territoire(territoire):
    # Accepte soit :
    # - un objet Path représentant un territoire ;
    # - directement son nom sous forme de texte.

    if isinstance(territoire, Path):
        nom_territoire = territoire.name
    else:
        nom_territoire = str(territoire)

    return (
        config.rapports_territoires_dir
        / f"{nom_territoire}.txt"
    )


def ecrire_rapport_territoire(
    territoire,
    texte
):
    # Écrit une information dans le rapport
    # détaillé d'un territoire.

    chemin = chemin_rapport_territoire(
        territoire
    )

    ajouter_ligne_fichier(
        chemin,
        texte
    )


def definir_territoire_rapport(territoire):
    # Définit le territoire actuellement résolu.
    #
    # À partir de cet instant, afficher_et_ecrire()
    # écrit à la fois dans :
    # - rapport_long.txt ;
    # - le rapport du territoire concerné.

    global territoire_rapport_actuel

    if territoire is None:
        territoire_rapport_actuel = None
        return

    if isinstance(territoire, Path):
        territoire_rapport_actuel = (
            territoire.name
        )
    else:
        territoire_rapport_actuel = (
            str(territoire)
        )


def afficher_et_ecrire(texte):
    # Journal technique complet.
    #
    # Les détails du moteur sont conservés uniquement
    # dans rapport_long.txt. Le rapport territorial est
    # alimenté séparément avec des informations synthétiques.

    ecrire_rapport_long(texte)


def symbole_survie(nombre_unites):
    # Symbole utilisé dans le rapport territorial lisible.

    if nombre_unites > 0:
        return "○"

    return "×"


def ecrire_entete_tableau_affrontements(
    territoire,
    colonne_numero
):
    bordure = "+------+--------------------------+-----+--------------------------+"

    ecrire_rapport_territoire(territoire, bordure)
    ecrire_rapport_territoire(
        territoire,
        f"| {colonne_numero:<4} | {'j1':<24} | {'':^3} | {'j2':<24} |"
    )
    ecrire_rapport_territoire(territoire, bordure)


def ecrire_fin_tableau_affrontements(territoire):
    ecrire_rapport_territoire(
        territoire,
        "+------+--------------------------+-----+--------------------------+"
    )


def ecrire_ligne_affrontement_territoire(
    territoire,
    etiquette,
    resultat
):
    symbole_1 = symbole_survie(resultat["final_1"])
    symbole_2 = symbole_survie(resultat["final_2"])

    gauche = (
        f"{resultat['general_1']} {symbole_1} "
        f"{resultat['initial_1']} → {resultat['final_1']}"
    )
    droite = (
        f"{resultat['general_2']} {symbole_2} "
        f"{resultat['initial_2']} → {resultat['final_2']}"
    )

    ecrire_rapport_territoire(
        territoire,
        f"| {str(etiquette):<4} | {gauche:<24} | {'<->':^3} | {droite:<24} |"
    )


def nom_type_unite(type_unite, nombre):
    singulier = {
        "archer": "archer",
        "piquier": "piquier",
        "cavalier": "cavalier",
        "vide": "vide",
    }
    pluriel = {
        "archer": "archers",
        "piquier": "piquiers",
        "cavalier": "cavaliers",
        "vide": "vide",
    }

    if nombre == 1:
        return singulier.get(type_unite, type_unite)
    return pluriel.get(type_unite, type_unite)


def formater_force_rapport(nombre, type_unite):
    return f"{nombre} {nom_type_unite(type_unite, nombre)}"


def ecrire_entete_detail_blocs(territoire):
    bordure = (
        "+--------+-----------+---------------+-----+-----------+---------------+----------------+"
    )
    ecrire_rapport_territoire(territoire, bordure)
    ecrire_rapport_territoire(
        territoire,
        "| Moment | Bloc j1   | Unités j1     |     | Bloc j2   | Unités j2     | Résultat       |"
    )
    ecrire_rapport_territoire(territoire, bordure)


def ecrire_fin_detail_blocs(territoire):
    ecrire_rapport_territoire(
        territoire,
        "+--------+-----------+---------------+-----+-----------+---------------+----------------+"
    )


def ecrire_detail_choc(territoire, detail):
    force_1 = formater_force_rapport(detail["initial_1"], detail["type_1"])
    force_2 = formater_force_rapport(detail["initial_2"], detail["type_2"])
    resultat = f"j1 ({detail['final_1']}) / j2 ({detail['final_2']})"

    ecrire_rapport_territoire(
        territoire,
        f"| {'Choc':<6} | {detail['bloc_1']:<9} | {force_1:<13} "
        f"| {'<->':^3} | {detail['bloc_2']:<9} | {force_2:<13} | {resultat:<14} |"
    )


def normaliser_manoeuvre(detail, joueur_1):
    if detail["joueur_attaquant"] == joueur_1:
        return {
            "bloc_1": detail["bloc_attaquant"],
            "type_1": detail["type_attaquant"],
            "initial_1": detail["initial_attaquant"],
            "final_1": detail["final_attaquant"],
            "bloc_2": detail["bloc_defenseur"],
            "type_2": detail["type_defenseur"],
            "initial_2": detail["initial_defenseur"],
            "final_2": detail["final_defenseur"],
            "fleche": "->",
        }

    return {
        "bloc_1": detail["bloc_defenseur"],
        "type_1": detail["type_defenseur"],
        "initial_1": detail["initial_defenseur"],
        "final_1": detail["final_defenseur"],
        "bloc_2": detail["bloc_attaquant"],
        "type_2": detail["type_attaquant"],
        "initial_2": detail["initial_attaquant"],
        "final_2": detail["final_attaquant"],
        "fleche": "<-",
    }


def ecrire_detail_manoeuvre(territoire, resultat_engagement, detail):
    normalise = normaliser_manoeuvre(
        detail,
        resultat_engagement["joueur_1"]
    )

    force_1 = formater_force_rapport(
        normalise["initial_1"],
        normalise["type_1"]
    )
    force_2 = formater_force_rapport(
        normalise["initial_2"],
        normalise["type_2"]
    )
    resultat = (
        f"j1 ({normalise['final_1']}) / "
        f"j2 ({normalise['final_2']})"
    )

    ecrire_rapport_territoire(
        territoire,
        f"| {('M' + str(detail['numero'])):<6} "
        f"| {normalise['bloc_1']:<9} | {force_1:<13} "
        f"| {normalise['fleche']:^3} "
        f"| {normalise['bloc_2']:<9} | {force_2:<13} "
        f"| {resultat:<14} |"
    )


def ecrire_detail_engagement(territoire, etiquette, resultat):
    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        f"--- Engagement {etiquette} : "
        f"j1 {resultat['general_1']} <-> j2 {resultat['general_2']} ---"
    )

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(territoire, "CHOC INITIAL")
    ecrire_rapport_territoire(territoire, "")

    if resultat["chocs"]:
        ecrire_entete_detail_blocs(territoire)
        for detail in resultat["chocs"]:
            ecrire_detail_choc(territoire, detail)
        ecrire_fin_detail_blocs(territoire)
    else:
        ecrire_rapport_territoire(territoire, "Aucun choc direct entre blocs.")

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(territoire, "MANŒUVRE")
    ecrire_rapport_territoire(territoire, "")

    if resultat["manoeuvres"]:
        ecrire_entete_detail_blocs(territoire)
        for detail in resultat["manoeuvres"]:
            ecrire_detail_manoeuvre(territoire, resultat, detail)
        ecrire_fin_detail_blocs(territoire)
    else:
        ecrire_rapport_territoire(territoire, "Aucune manœuvre.")

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        f"Résultat : j1 {resultat['general_1']} "
        f"{resultat['initial_1']} → {resultat['final_1']} | "
        f"j2 {resultat['general_2']} "
        f"{resultat['initial_2']} → {resultat['final_2']}"
    )


def ecrire_details_engagements(territoire, engagements):
    if not engagements:
        return

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        "================ DÉTAIL DES AFFRONTEMENTS ================"
    )

    for etiquette, resultat in engagements:
        ecrire_detail_engagement(
            territoire,
            etiquette,
            resultat
        )


def preparer_rapports():
    # Prépare tous les rapports du nouveau tour.
    #
    # Les rapports du tour précédent sont effacés.
    # Une nouvelle météo est ensuite générée.

    global meteo_tour
    global territoire_rapport_actuel

    territoire_rapport_actuel = None

    config.rapport_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    config.rapports_territoires_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Effacer les rapports généraux.
    config.rapport_court_path.write_text(
        "",
        encoding="utf-8"
    )

    config.rapport_long_path.write_text(
        "",
        encoding="utf-8"
    )

    # Préparer un rapport pour chaque territoire.
    for territory in config.territoires:
        chemin = chemin_rapport_territoire(
            territory
        )

        chemin.write_text(
            "",
            encoding="utf-8"
        )

    # Générer la météo commune au tour.
    meteo_tour = etat.choisir_meteo_tour()

    etat.sauvegarder_meteo(
        meteo_tour
    )

    # ------------------------------------------
    # Rapport court public
    # ------------------------------------------

    ecrire_rapport_court(
        "=== RÉSUMÉ DU TOUR ==="
    )

    ecrire_rapport_court("")

    ecrire_rapport_court(
        f"MÉTÉO : {meteo_tour}"
    )

    ecrire_rapport_court("")

    # ------------------------------------------
    # Rapport long complet
    # ------------------------------------------

    ecrire_rapport_long(
        "=== RAPPORT LONG DU TOUR ==="
    )

    ecrire_rapport_long("")

    ecrire_rapport_long(
        f"Météo du tour : {meteo_tour}"
    )

    ecrire_rapport_long(
        "Effet actuel de la météo : aucun"
    )

    ecrire_rapport_long("")

    # ------------------------------------------
    # Rapports territoriaux
    # ------------------------------------------

    for territory in config.territoires:
        ecrire_rapport_territoire(
            territory,
            (
                f"=== RAPPORT DE "
                f"{territory.name.upper()} ==="
            )
        )

        ecrire_rapport_territoire(
            territory,
            ""
        )

        ecrire_rapport_territoire(
            territory,
            f"Météo : {meteo_tour}"
        )

        ecrire_rapport_territoire(
            territory,
            ""
        )


def afficher_fin_de_tour():
    # Affiche automatiquement le rapport court
    # dans le terminal.
    #
    # Pour les autres rapports, affiche seulement
    # des commandes prêtes à copier-coller.

    print()
    print("=" * 48)
    print("                 RAPPORT COURT")
    print("=" * 48)
    print()

    if config.rapport_court_path.exists():
        contenu = config.rapport_court_path.read_text(
            encoding="utf-8"
        ).strip()

        if contenu:
            print(contenu)
        else:
            print("Le rapport court est vide.")
    else:
        print("Le rapport court est introuvable.")

    print()
    print("=" * 48)
    print("            CONSULTER LES RAPPORTS")
    print("=" * 48)
    print()

    print("Rapport long complet :")
    print(
        f"cat {config.rapport_long_path}"
    )

    print()

    print("Exemple de rapport territorial :")
    print(
        "cat "
        f"{config.rapports_territoires_dir / 'terrain1.txt'}"
    )

    print()

    print("Liste des rapports territoriaux :")
    print(
        f"ls {config.rapports_territoires_dir}/"
    )

    print()
