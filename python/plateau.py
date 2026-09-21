"""Préparation du plateau, résolution territoriale et contrôle de la carte."""
import grp
import os
import pwd

import combats
import config
import etat
import generaux
import rapports


def territoires_ravitailles(joueur, controle_territoires):
    if joueur == "j1":
        base = "base1"
    else:
        base = "base2"

    ravitailles = set()
    a_explorer = [base]

    while a_explorer:
        territoire_actuel = a_explorer.pop()

        if territoire_actuel in ravitailles:
            continue

        if controle_territoires.get(territoire_actuel) != joueur:
            continue

        ravitailles.add(territoire_actuel)

        for voisin in config.carte_territoires.get(territoire_actuel, []):
            if voisin not in ravitailles:
                a_explorer.append(voisin)

    return ravitailles


def sauvegarder_controle_territoires():
    # Sauvegarde le contrôle des territoires après la résolution.
    #
    # Ce fichier servira au prochain tour pour savoir
    # qui défend un territoire.

    lignes = []

    for territory in config.territoires:
        generaux_territoire = generaux.lire_generaux_territoire(territory)
        controle = generaux.controle_territoire_generaux(generaux_territoire)

        lignes.append(f"{territory.name}={controle}")

    config.controle_territoires_path.parent.mkdir(exist_ok=True)
    config.controle_territoires_path.write_text("\n".join(lignes), encoding="utf-8")


def lancer_bataille_v15():
    # Boucle de résolution V1.5.
    #
    # Elle décide :
    # - OFF/OFF si le territoire était neutre
    #   ou contesté avant ;
    # - OFF/DEF si le territoire appartenait
    #   à un joueur avant.
    #
    # Le rapport court ne reçoit que les
    # informations publiques.
    #
    # Le rapport long et le rapport territorial
    # reçoivent les informations détaillées.

    rapports.afficher_et_ecrire(
        "\n=== RÉSOLUTION MYTHODEA V1.5 ==="
    )

    controle_avant_resolution = (
        etat.charger_controle_territoires()
    )

    for territory in config.territoires:
        rapports.definir_territoire_rapport(
            territory
        )

        ancien_controle = (
            controle_avant_resolution.get(
                territory.name,
                "neutre"
            )
        )

        rapports.afficher_et_ecrire("")
        rapports.afficher_et_ecrire("")

        rapports.afficher_et_ecrire(
            f"=== TERRITOIRE : "
            f"{territory.name.upper()} ==="
        )

        rapports.afficher_et_ecrire("")

        rapports.afficher_et_ecrire(
            f"Contrôle avant le tour : "
            f"{ancien_controle}"
        )

        generaux_territoire = (
            generaux.lire_generaux_territoire(
                territory
            )
        )

        controle_avant_combat = (
            generaux.controle_territoire_generaux(
                generaux_territoire
            )
        )

        rapports.afficher_et_ecrire(
            f"Contrôle après les déplacements : "
            f"{controle_avant_combat}"
        )

        total_initial_j1 = generaux.total_unites_joueur_generaux(
            generaux_territoire,
            "j1"
        )
        total_initial_j2 = generaux.total_unites_joueur_generaux(
            generaux_territoire,
            "j2"
        )

        # Rapport territorial lisible.
        rapports.chemin_rapport_territoire(
            territory
        ).write_text(
            "",
            encoding="utf-8"
        )

        rapports.ecrire_rapport_territoire(
            territory,
            "=" * 56
        )
        rapports.ecrire_rapport_territoire(
            territory,
            f"{territory.name.upper()} — RAPPORT DE BATAILLE"
        )
        rapports.ecrire_rapport_territoire(
            territory,
            "=" * 56
        )
        rapports.ecrire_rapport_territoire(
            territory,
            ""
        )
        rapports.ecrire_rapport_territoire(
            territory,
            f"Météo            : {rapports.meteo_tour}"
        )
        rapports.ecrire_rapport_territoire(
            territory,
            f"Contrôle initial : {ancien_controle}"
        )
        generaux_initiaux_j1 = len(generaux.generaux_actifs_joueur(generaux_territoire, "j1"))
        generaux_initiaux_j2 = len(generaux.generaux_actifs_joueur(generaux_territoire, "j2"))

        rapports.ecrire_rapport_territoire(
            territory,
            f"Forces initiales : j1 = {total_initial_j1} | j2 = {total_initial_j2}"
        )
        rapports.ecrire_rapport_territoire(
            territory,
            f"Généraux engagés: j1 = {generaux_initiaux_j1} | j2 = {generaux_initiaux_j2}"
        )
        rapports.ecrire_rapport_territoire(
            territory,
            ""
        )
        rapports.ecrire_rapport_territoire(
            territory,
            "Légende : ○ survivant | × détruit | effectif initial → effectif final"
        )

        # --------------------------------------
        # Présence initiale
        # --------------------------------------

        rapports.afficher_et_ecrire(
            "\n--- Présence avant combat ---"
        )

        for joueur in config.joueurs:
            rapports.afficher_et_ecrire(
                f"\n{joueur} :"
            )

            for emplacement in config.emplacements:
                general = (
                    generaux_territoire[
                        joueur
                    ][
                        emplacement
                    ]
                )

                if general is None:
                    rapports.afficher_et_ecrire(
                        f"emplacement "
                        f"{emplacement} : vide"
                    )

                    continue

                rapports.afficher_et_ecrire(
                    f"emplacement "
                    f"{emplacement} : "
                    f"{general['nom']} "
                    f"({general['total_unites']} unités)"
                )

                # Informations de niveau renseignement.
                # Elles sont visibles dans le rapport long
                # et territorial pendant la V1.5.
                fiche = general["fiche"]

                rapports.afficher_et_ecrire(
                    f"  orientation : "
                    f"{fiche.get('orientation', 'inconnue')}"
                )

                rapports.afficher_et_ecrire(
                    f"  stratégie : "
                    f"{fiche.get('strategie', 'inconnue')}"
                )

                rapports.afficher_et_ecrire(
                    f"  force : "
                    f"{fiche.get('force', 'inconnue')}"
                )

                rapports.afficher_et_ecrire(
                    f"  expérience : "
                    f"{fiche.get('experience', 'inconnue')}"
                )

                if etat.general_est_fatigue(general):
                    rapports.afficher_et_ecrire(
                        "  fatigue : oui"
                    )
                else:
                    rapports.afficher_et_ecrire(
                        "  fatigue : non"
                    )

                if len(general["ordres"]) == 0:
                    rapports.afficher_et_ecrire(
                        "  ordres : aucun ordre valide"
                    )
                else:
                    textes_ordres = [
                        ordre["texte"]
                        for ordre
                        in general["ordres"]
                    ]

                    rapports.afficher_et_ecrire(
                        "  ordres : "
                        + ", ".join(
                            textes_ordres
                        )
                    )

        # --------------------------------------
        # Combat
        # --------------------------------------

        combat_declenche = False
        mode_combat = None

        if controle_avant_combat == "conteste":
            combat_declenche = True

            if ancien_controle in config.joueurs:
                mode_combat = "OFF/DEF"

                rapports.ecrire_rapport_territoire(
                    territory,
                    f"Mode de combat   : {mode_combat} ({ancien_controle} défend)"
                )

                rapports.afficher_et_ecrire(
                    f"\nCombat détecté : "
                    f"OFF/DEF. "
                    f"{ancien_controle} défend."
                )

                combats.resoudre_combat_off_def(
                    territory,
                    ancien_controle
                )

            else:
                mode_combat = "OFF/OFF"

                rapports.ecrire_rapport_territoire(
                    territory,
                    f"Mode de combat   : {mode_combat}"
                )

                rapports.afficher_et_ecrire(
                    "\nCombat détecté : OFF/OFF."
                )

                combats.resoudre_combat_v15(
                    territory
                )

        else:
            rapports.afficher_et_ecrire(
                "\nAucun combat sur ce territoire."
            )

        # --------------------------------------
        # Situation finale
        # --------------------------------------

        generaux_finaux = (
            generaux.lire_generaux_territoire(
                territory
            )
        )

        controle_final = (
            generaux.controle_territoire_generaux(
                generaux_finaux
            )
        )

        rapports.afficher_et_ecrire(
            f"\nContrôle final : "
            f"{controle_final}"
        )

        rapports.afficher_et_ecrire(
            "\n--- Forces survivantes ---"
        )

        totaux_finaux = {}

        for joueur in config.joueurs:
            total_joueur = (
                generaux.total_unites_joueur_generaux(
                    generaux_finaux,
                    joueur
                )
            )
            totaux_finaux[joueur] = total_joueur

            rapports.afficher_et_ecrire(
                f"{joueur} : "
                f"{total_joueur} unité(s)"
            )

        rapports.ecrire_rapport_territoire(
            territory,
            ""
        )
        generaux_survivants_j1 = len(
            generaux.generaux_actifs_joueur(generaux_finaux, "j1")
        )
        generaux_survivants_j2 = len(
            generaux.generaux_actifs_joueur(generaux_finaux, "j2")
        )

        pertes_j1 = total_initial_j1 - totaux_finaux["j1"]
        pertes_j2 = total_initial_j2 - totaux_finaux["j2"]

        generaux_detruits_j1 = max(
            0,
            generaux_initiaux_j1 - generaux_survivants_j1
        )
        generaux_detruits_j2 = max(
            0,
            generaux_initiaux_j2 - generaux_survivants_j2
        )

        rapports.ecrire_rapport_territoire(
            territory,
            "===================== BILAN ====================="
        )
        rapports.ecrire_rapport_territoire(territory, "")

        bordure_bilan = "+----------------------+--------+--------+"
        rapports.ecrire_rapport_territoire(territory, bordure_bilan)
        rapports.ecrire_rapport_territoire(
            territory,
            f"| {'':<20} | {'j1':<6} | {'j2':<6} |"
        )
        rapports.ecrire_rapport_territoire(territory, bordure_bilan)

        lignes_bilan = [
            ("Forces initiales", total_initial_j1, total_initial_j2),
            ("Forces restantes", totaux_finaux["j1"], totaux_finaux["j2"]),
            ("Pertes", pertes_j1, pertes_j2),
            ("Généraux engagés", generaux_initiaux_j1, generaux_initiaux_j2),
            ("Généraux survivants", generaux_survivants_j1, generaux_survivants_j2),
            ("Généraux détruits", generaux_detruits_j1, generaux_detruits_j2),
        ]

        for libelle, valeur_j1, valeur_j2 in lignes_bilan:
            rapports.ecrire_rapport_territoire(
                territory,
                f"| {libelle:<20} | {str(valeur_j1):<6} | {str(valeur_j2):<6} |"
            )

        rapports.ecrire_rapport_territoire(territory, bordure_bilan)
        rapports.ecrire_rapport_territoire(territory, "")
        rapports.ecrire_rapport_territoire(
            territory,
            f"Contrôle final : {controle_final}"
        )

        # --------------------------------------
        # Informations publiques
        # --------------------------------------

        if combat_declenche:
            rapports.ecrire_rapport_court(
                f"{territory.name} : "
                f"combat {mode_combat}"
            )

            rapports.ecrire_rapport_court(
                f"{territory.name} : "
                f"contrôle final = "
                f"{controle_final}"
            )

        elif ancien_controle != controle_final:
            # Changement de contrôle sans combat,
            # par exemple occupation d'un territoire vide.
            rapports.ecrire_rapport_court(
                f"{territory.name} : "
                f"changement de contrôle "
                f"{ancien_controle} -> "
                f"{controle_final}"
            )

        rapports.definir_territoire_rapport(
            None
        )

    sauvegarder_controle_territoires()

    # ------------------------------------------
    # Contrôle public final de la carte
    # ------------------------------------------

    rapports.ecrire_rapport_court("")

    rapports.ecrire_rapport_court(
        "CONTRÔLE FINAL"
    )

    controle_final_carte = (
        etat.charger_controle_territoires()
    )

    for territory in config.territoires:
        controle = controle_final_carte.get(
            territory.name,
            "neutre"
        )

        rapports.ecrire_rapport_court(
            f"{territory.name} : {controle}"
        )


def reparer_structure():
    # 1. Créer les emplacements dans les territoires
    for territory in config.territoires:
        for joueur in config.joueurs:
            joueur_dir = territory / joueur
            joueur_dir.mkdir(exist_ok=True)

            uid = pwd.getpwnam(joueur).pw_uid
            gid = grp.getgrnam(joueur).gr_gid

            os.chown(joueur_dir, uid, gid)
            os.chmod(joueur_dir, 0o700)

            for emplacement in config.emplacements:
                emplacement_dir = joueur_dir / emplacement
                emplacement_dir.mkdir(exist_ok=True)

                os.chown(emplacement_dir, uid, gid)
                os.chmod(emplacement_dir, 0o700)

        # Créer les zones de repli.
    for joueur in config.joueurs:
        repli_joueur = config.repli_path / joueur
        repli_joueur.mkdir(parents=True, exist_ok=True)

        uid = pwd.getpwnam(joueur).pw_uid
        gid = grp.getgrnam(joueur).gr_gid

        os.chown(repli_joueur, uid, gid)
        os.chmod(repli_joueur, 0o700)



    # 2. Faire apparaître un général par joueur si possible.
    for joueur in config.joueurs:
        generaux.faire_apparaitre_general_si_possible(joueur)
