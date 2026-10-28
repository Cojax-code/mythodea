"""Calcul des combats, choc initial, manœuvres et combat rangé."""
import random
from fractions import Fraction

import catalogues
import bouclier_vivant
import config
import etat
import generaux
import rapports
import progression
import ordres_calculs_v2
import ordres_pipeline
import soldats
import unites


def adversaire_du_duel(armee, joueur):
    """Le duel fournit ses deux participants, indépendamment de leurs noms."""
    if len(armee) != 2 or joueur not in armee:
        raise ValueError("Un duel doit contenir exactement deux adversaires.")
    return next(adversaire for adversaire in armee if adversaire != joueur)


def camps_du_combat(configuration):
    camps = tuple(dict.fromkeys(acteur["camp"] for acteur in configuration["acteurs"].values()))
    if len(camps) != 2:
        raise ValueError("Une bataille doit opposer exactement deux camps.")
    return camps


def combat_entre_generaux(general_1, general_2, *, participants=None,
                          avant_exclus_manoeuvre=False):
    if (general_1['joueur'] == general_2['joueur'] or
            general_1.get('camp', general_1['joueur']) == general_2.get('camp', general_2['joueur'])):
        raise ValueError("Un duel doit opposer deux généraux de camps différents.")
    participants = participants if participants is not None else soldats.VueParticipants()
    participants.verifier_duel(general_1, general_2)
    with ordres_pipeline.duel(general_1, general_2) as decisions:
        with ordres_pipeline.participations_duel(general_1, general_2, participants, decisions) as vue:
            with unites.duel(general_1, general_2):
                for general in (general_1, general_2):
                    if vue.present(general):
                        vue.participer(general)
                initiales = [vue.total(g) for g in (general_1, general_2)]
                rafales = ordres_pipeline.rafales(general_1, general_2, random,
                    lambda infos, n, g: supprimer_unites(infos, n, g, participants=vue),
                    participants=vue)
                resultat = _combat_entre_generaux(
                    general_1, general_2, participants=vue,
                    avant_exclus_manoeuvre=avant_exclus_manoeuvre)
                if rafales:
                    resultat['initial_1'], resultat['initial_2'] = initiales
                    resultat['rafales'] = rafales
            for numero, general in enumerate((general_1, general_2), 1):
                vue.supprimer_general_si_vide(general)
                resultat[f'final_{numero}'] = vue.total(general)
    if decisions:
        resultat['ordres_v2'] = decisions
    return resultat



def retirer_avants_de_manoeuvre(armee):
    """Vue de manœuvre sans Avant de Muraille, sans mutation des soldats.

    La suppression est seulement logique : les blocs restent sur disque,
    conservent leurs UUID et peuvent retourner à leur général après le choc.
    Ni attaque depuis Avant, ni ciblage d'Avant pendant cette manœuvre.
    """
    resultat = {}
    for joueur, blocs in armee.items():
        copies = dict(blocs)
        if 'avant' in copies:
            copies['avant'] = dict(copies['avant'], nombre=0, unites=[])
        resultat[joueur] = copies
    return resultat


def _combat_entre_generaux(general_1, general_2, *, participants=None,
                            avant_exclus_manoeuvre=False):
    # Affrontement complet entre deux généraux.
    # Muraille peut retirer les Avant de la manœuvre sans détruire leurs soldats.
    #
    # Déroulement :
    # 1. Choc initial entre les blocs placés face à face.
    # 2. Manœuvres entre les blocs survivants.

    participants = participants if participants is not None else soldats.VueParticipants()
    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]
    camp_1 = general_1.get("camp", joueur_1)
    camp_2 = general_2.get("camp", joueur_2)
    if camp_1 == camp_2 or joueur_1 == joueur_2:
        raise ValueError("Un duel doit opposer deux généraux de camps différents.")

    initial_1 = participants.total(general_1)
    initial_2 = participants.total(general_2)

    # Rafale peut avoir éliminé un camp avant tout choc ou priorité de bouclier.
    if not participants.present(general_1) or not participants.present(general_2):
        return dict(joueur_1=joueur_1, joueur_2=joueur_2, camp_1=camp_1, camp_2=camp_2,
                    general_1=general_1['nom'], general_2=general_2['nom'],
                    affichage_1=rapports.nom_affichage_general(general_1),
                    affichage_2=rapports.nom_affichage_general(general_2),
                    initial_1=initial_1, initial_2=initial_2, final_1=initial_1, final_2=initial_2,
                    chocs=[], manoeuvres=[])

    rapports.afficher_et_ecrire(
        f"\nEngagement : "
        f"{joueur_1} {rapports.nom_affichage_general(general_1)} VS "
        f"{joueur_2} {rapports.nom_affichage_general(general_2)}"
    )

    details_bouclier = []
    if (bouclier_vivant.presence_bouclier(general_1)
            or bouclier_vivant.presence_bouclier(general_2)):
        zombie, ennemi = (general_1, general_2) if bouclier_vivant.presence_bouclier(general_1) else (general_2, general_1)
        termine, details_bouclier = bouclier_vivant.resoudre_priorite(zombie, ennemi, participants=participants)
        if zombie is general_2:
            # Les colonnes des rapports suivent general_1 / general_2.
            details_bouclier = [
                dict(d, **{f'{cle}_1': d[f'{cle}_2'] for cle in ('bloc', 'type', 'initial', 'final')},
                     **{f'{cle}_2': d[f'{cle}_1'] for cle in ('bloc', 'type', 'initial', 'final')})
                for d in details_bouclier
            ]
        if termine:
            return {
                "joueur_1": joueur_1, "camp_1": camp_1, "camp_2": camp_2,
                "general_1": general_1["nom"],
                "affichage_1": rapports.nom_affichage_general(general_1),
                "initial_1": initial_1,
                "final_1": participants.total(general_1),
                "joueur_2": joueur_2, "general_2": general_2["nom"],
                "affichage_2": rapports.nom_affichage_general(general_2),
                "initial_2": initial_2,
                "final_2": participants.total(general_2),
                "chocs": details_bouclier, "manoeuvres": [],
            }

    initiative_avant, details_choc = phase_engagement_initial(
        general_1,
        general_2, participants=participants
    )
    details_choc = details_bouclier + details_choc

    details_manoeuvre = []

    fuites = ordres_pipeline.fuir_apres_choc((general_1, general_2))
    # Le choc peut avoir détruit un général ou déclenché une retraite acceptée.
    if fuites or not participants.present(general_1) or not participants.present(general_2):
        return {
            "joueur_1": joueur_1,
            "camp_1": camp_1,
            "camp_2": camp_2,
            "general_1": general_1["nom"],
            "affichage_1": rapports.nom_affichage_general(general_1),
            "initial_1": initial_1,
            "final_1": participants.total(general_1),
            "joueur_2": joueur_2,
            "general_2": general_2["nom"],
            "affichage_2": rapports.nom_affichage_general(general_2),
            "initial_2": initial_2,
            "final_2": participants.total(general_2),
            "chocs": details_choc,
            "manoeuvres": details_manoeuvre,
            "fuites": fuites,
        }

    rapports.afficher_et_ecrire("\n=== MANŒUVRE ===")

    tour = 0
    numero_manoeuvre = 0

    while tour < 10:
        tour += 1

        if not participants.present(general_1) or not participants.present(general_2):
            break

        armee = {
            joueur_1: participants.blocs(general_1),
            joueur_2: participants.blocs(general_2),
        }
        if avant_exclus_manoeuvre:
            armee = retirer_avants_de_manoeuvre(armee)

        if (
            generaux.total_unites_general(armee[joueur_1]) == 0
            or generaux.total_unites_general(armee[joueur_2]) == 0
        ):
            break

        rapports.afficher_et_ecrire(f"\n--- Tour de manœuvre {tour} ---")
        attaque_effectuee = False

        actions = ordre_actions_manoeuvre(armee, initiative_avant)
        # Tri stable : l'ordre existant départage les autres actions. Chaque
        # bloc conserve son unique action du tour, sans attaque supplémentaire.
        generaux_du_duel = {g['joueur']: g for g in (general_1, general_2)}
        actions.sort(key=lambda action: not (
            armee[action[0]][action[1]]['type'] == 'chevalier_clinquant'
            and ordres_pipeline.effet(generaux_du_duel[action[0]], 'etincellant')))
        rapports.afficher_et_ecrire(
            "\nOrdre global de manœuvre : "
            + ", ".join(f"{joueur} {bloc}" for joueur, bloc in actions)
        )

        for joueur_attaquant, bloc_attaquant in actions:
            if not participants.present(general_1) or not participants.present(general_2):
                break

            armee = {
                joueur_1: participants.blocs(general_1),
                joueur_2: participants.blocs(general_2),
            }
            if avant_exclus_manoeuvre:
                armee = retirer_avants_de_manoeuvre(armee)

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
                infos_attaquant["type"],
                general_1 if joueur_attaquant == joueur_1 else general_2,
                general_2 if joueur_attaquant == joueur_1 else general_1,
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
                cible, participants=participants
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

    if participants.present(general_1):
        participants.supprimer_general_si_vide(general_1)
    if participants.present(general_2):
        participants.supprimer_general_si_vide(general_2)

    return {
        "joueur_1": joueur_1,
        "camp_1": camp_1,
        "camp_2": camp_2,
        "general_1": general_1["nom"],
        "affichage_1": rapports.nom_affichage_general(general_1),
        "initial_1": initial_1,
        "final_1": participants.total(general_1),
        "joueur_2": joueur_2,
        "general_2": general_2["nom"],
        "affichage_2": rapports.nom_affichage_general(general_2),
        "initial_2": initial_2,
        "final_2": participants.total(general_2),
        "chocs": details_choc,
        "manoeuvres": details_manoeuvre,
    }


def resoudre_attaque_frontale(
    territory,
    mode_combat,
    configuration=None
):
    if configuration is None:
        configuration = config.configuration_mode("classique")
    camp_1, camp_2 = camps_du_combat(configuration)

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

    for emplacement in configuration["emplacements"]:

        # Relire entièrement le territoire avant
        # chaque duel, car le duel précédent peut
        # avoir supprimé un général.
        generaux_territoire = (
            generaux.lire_forces_territoire(
                territory, configuration
            )
        )

        general_camp_1 = (
            generaux_territoire[
                camp_1
            ][
                emplacement
            ]
        )

        general_camp_2 = (
            generaux_territoire[
                camp_2
            ][
                emplacement
            ]
        )

        formations = ordres_pipeline.formations_retenues(generaux_territoire)
        if any(g is not None and not progression.general_recoit_ordre(g, 'attaque_frontale')
               for g in (general_camp_1, general_camp_2)):
            continue  # Le Zombie garde sa participation au combat rangé normal.
        if (ordres_pipeline.qg_hors_formation(general_camp_1, formations.get(camp_1))
                or ordres_pipeline.qg_hors_formation(general_camp_2, formations.get(camp_2))):
            rapports.ecrire_rapport_territoire(territory,
                f'Emplacement {emplacement} : QG_nommade hors engagement frontal ; '
                'les emplacements des autres généraux sont conservés.')
            continue

        # Il faut un général actif dans les deux camps
        # au même emplacement.
        if not generaux.general_a_des_unites(
            general_camp_1
        ):
            rapports.afficher_et_ecrire(
                f"Emplacement {emplacement} : "
                f"aucun général actif pour {camp_1}."
            )

            continue

        if not generaux.general_a_des_unites(
            general_camp_2
        ):
            rapports.afficher_et_ecrire(
                f"Emplacement {emplacement} : "
                f"aucun général actif pour {camp_2}."
            )

            continue

        engagement_effectue = True

        rapports.afficher_et_ecrire(
            f"\n--- Duel frontal "
            f"{mode_combat} : "
            f"emplacement {emplacement} ---"
        )

        rapports.afficher_et_ecrire(
            f"{rapports.nom_affichage_general(general_camp_1)} "
            f"contre "
            f"{rapports.nom_affichage_general(general_camp_2)}"
        )

        resultat_duel = combat_entre_generaux(
            general_camp_1,
            general_camp_2
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



def preparer_muraille_territoire(forces, formations, camp, general_adverse, *,
                                aleatoire, reserve_strategique=None):
    """Prépare le prochain choc collectif depuis les forces territoriales.

    Lecture seule : les exclusions des rôles viennent du pipeline, puis la
    sélection relit les blocs Avant. Un ordre absent/annulé ne déclenche rien.
    L'engagement et les pertes restent sous contrôle du pilote territorial.
    """
    participants = ordres_pipeline.participants_muraille_territoire(
        forces, formations, camp, reserve_strategique=reserve_strategique)
    if not participants:
        return dict(choisi=None, previsions=(), participants=())
    formation = formations[camp]
    qg_exclu = (formation['qg']
               if 'qg_nommade' in formation['ordres'] else None)
    decision = prochain_avant_muraille(
        participants, general_adverse, aleatoire=aleatoire,
        qg_nommade=qg_exclu, reserve_strategique=reserve_strategique)
    return dict(decision, participants=participants)


def resoudre_combat_range(
    territory,
    mode_combat,
    configuration=None
):
    if configuration is None:
        configuration = config.configuration_mode("classique")
    resoudre_affrontement_actif(territory, mode_combat, configuration)
    # L'affrontement est terminé : préparer la tête de colonne avant le choix
    # de retraite, sans engager les nouveaux actifs dans cette bataille.
    promus = generaux.remonter_renforts_bot(territory, configuration)
    if promus:
        forces = generaux.lire_forces_territoire(territory, configuration)
        rapports.afficher_et_ecrire(
            f"Colonne ennemie : {len(promus)} renfort(s) remonté(s). "
            f"Contrôle après remontée : {generaux.controle_forces(forces)}"
        )
    return promus


def resoudre_affrontement_actif(
    territory,
    mode_combat,
    configuration=None
):
    if configuration is None:
        configuration = config.configuration_mode("classique")
    with ordres_pipeline.bataille(territory, configuration):
        return _resoudre_affrontement_actif(territory, mode_combat, configuration)


def _resoudre_affrontement_actif(territory, mode_combat, configuration):
    camp_1, camp_2 = camps_du_combat(configuration)

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
        generaux.lire_forces_territoire(
            territory, configuration
        )
    )

    ordre_frontal_camp_1 = (
        generaux.joueur_possede_ordre_armee(
            generaux_depart,
            camp_1,
            "1-2"
        )
    )

    ordre_frontal_camp_2 = (
        generaux.joueur_possede_ordre_armee(
            generaux_depart,
            camp_2,
            "1-2"
        )
    )

    ordre_frontal_camp_1 = ordre_frontal_camp_1 and ordres_pipeline.frontal_autorise(camp_1)
    ordre_frontal_camp_2 = ordre_frontal_camp_2 and ordres_pipeline.frontal_autorise(camp_2)

    # Un frontal restant autorisé suffit à déclencher les couples de positions.
    # Le pipeline a déjà traité les conflits internes et l'opposition On_melange.
    if ordre_frontal_camp_1 or ordre_frontal_camp_2:

        camps = []

        if ordre_frontal_camp_1:
            camps.append(camp_1)

        if ordre_frontal_camp_2:
            camps.append(camp_2)

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
            "Pos", (camp_1, camp_2)
        )

        engagements_frontaux = resoudre_attaque_frontale(
            territory,
            mode_combat, configuration
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
            generaux.lire_forces_territoire(
                territory, configuration
            )
        )

        controle = (
            generaux.controle_forces(
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

        actifs_camp_1 = generaux.generaux_actifs_joueur(
            generaux_territoire,
            camp_1
        )

        actifs_camp_2 = generaux.generaux_actifs_joueur(
            generaux_territoire,
            camp_2
        )

        if (
            len(actifs_camp_1) == 0
            or len(actifs_camp_2) == 0
        ):
            controle = (
                generaux.controle_forces(
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

        formations = ordres_pipeline.formations_retenues(generaux_territoire)
        general_camp_1 = ordres_pipeline.generaux_en_formation(
            actifs_camp_1, formations.get(camp_1))[0]
        general_camp_2 = ordres_pipeline.generaux_en_formation(
            actifs_camp_2, formations.get(camp_2))[0]

        # Préparer les formations collectives au point d'entrée territorial.
        # Tant que leur résolution multi-généraux n'est pas raccordée, refuser
        # explicitement l'activation plutôt que jouer un duel ordinaire faux.
        murailles = {}
        for camp, adversaire in ((camp_1, general_camp_2),
                                 (camp_2, general_camp_1)):
            if 'muraille_humaine' in formations.get(camp, {}).get('ordres', ()):
                simulateur = random.Random()
                simulateur.setstate(random.getstate())
                murailles[camp] = preparer_muraille_territoire(
                    generaux_territoire, formations, camp, adversaire,
                    aleatoire=simulateur)
        if murailles:
            # Aucun changement sur les unités tant que le cycle territorial,
            # y compris le combat des autres blocs et son rapport, n'est pas
            # entièrement raccordé.
            if len(murailles) != 1:
                raise NotImplementedError(
                    'Muraille contre Muraille : confrontation collective à définir.')
            raise NotImplementedError(
                'Muraille : chocs collectifs disponibles mais cycle territorial '
                'et rapports encore incomplets ; aucun soldat modifié.')

        rapports.afficher_et_ecrire(
            f"\n--- Combat rangé "
            f"{mode_combat} "
            f"{round_combat} ---"
        )

        resultat_combat_range = combat_entre_generaux(
            general_camp_1,
            general_camp_2
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
                "Tour", (camp_1, camp_2)
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
        generaux.lire_forces_territoire(
            territory, configuration
        )
    )

    controle = (
        generaux.controle_forces(
            generaux_territoire
        )
    )

    rapports.afficher_et_ecrire(
        f"Limite de rounds atteinte "
        f"sur {territory.name}. "
        f"Controle actuel : {controle}"
    )


def resoudre_combat_v15(territory, configuration=None):
    # Résolution OFF/OFF.

    rapports.afficher_et_ecrire(
        f"\n=== Combat OFF/OFF sur {territory.name} ==="
    )

    resoudre_combat_range(
        territory,
        "OFF/OFF", configuration
    )


def resoudre_combat_off_def(territory, defenseur, configuration=None):
    # Résolution OFF/DEF.
    #
    # Pour l'instant, le moteur de combat est le même que OFF/OFF.
    # Mais on garde la distinction défenseur / attaquant pour les règles futures :
    # terrain, fortification, ravitaillement, avant-poste, brouillard de guerre, etc.

    if configuration is None:
        configuration = config.configuration_mode("classique")
    camps = camps_du_combat(configuration)
    if defenseur not in camps:
        raise ValueError("Le défenseur doit être un camp du combat.")
    attaquant = next(camp for camp in camps if camp != defenseur)

    rapports.afficher_et_ecrire(
        f"\n=== Combat OFF/DEF sur {territory.name} ==="
    )
    rapports.afficher_et_ecrire(
        f"Défenseur : {defenseur} | Attaquant : {attaquant}"
    )

    resoudre_combat_range(territory, "OFF/DEF", configuration)


def cible_facile(type_unite):
    if type_unite == "archer":
        return "piquier"

    if type_unite == "piquier":
        return "cavalier"

    if type_unite == "cavalier":
        return "archer"

    return None


def multiplicateur(type_attaquant, type_defenseur, general_attaquant=None, general_defenseur=None):
    valeur = unites.avantage(type_attaquant, type_defenseur, general_attaquant, general_defenseur)
    if (type_attaquant == 'piquier' and unites.etiquette(type_defenseur, 'cavalerie')
            and ordres_pipeline.effet(general_attaquant, 'herisson')):
        valeur = max(valeur, 3)
    if (type_defenseur == 'piquier' and unites.etiquette(type_attaquant, 'distance')
            and ordres_pipeline.effet(general_defenseur, 'herisson')):
        valeur = max(valeur, 3)
    return valeur


def valeur_base_bloc(infos, bloc=None):
    """Valeur individuelle, avec la formation lourde recalculée à chaque choc."""
    if infos['nombre'] == 0:
        return 0
    valeur = catalogues.valeur_combat(infos['type'])
    if bloc == 'avant':
        valeur = unites.definition(infos['type']).get('valeur_avant', valeur)
    if infos['type'] == 'cavalerie_lourde' and bloc == 'avant' and infos['nombre'] >= 15:
        valeur *= 2
    return valeur


def bonus_fatigue(nombre_1, fatigue_1, nombre_2, fatigue_2):
    """Équivalents de frais avantagés, sans paire d'UUID ni tirage.

    Une fatigue est un booléen collectif ou une séquence de booléens individuels.
    Priorités : fatigués/fatigués, frais/fatigués, frais/frais ; seuls les frais
    restants reçoivent le complément proportionnel à la fatigue adverse initiale.
    """
    fatigues = []
    for nombre, fatigue in ((nombre_1, fatigue_1), (nombre_2, fatigue_2)):
        if type(fatigue) is bool:
            fatigues.append(nombre if fatigue else 0)
        elif (isinstance(fatigue, (tuple, list)) and len(fatigue) == nombre
              and all(type(valeur) is bool for valeur in fatigue)):
            fatigues.append(sum(fatigue))
        else:
            raise ValueError('Fatigue : un booléen ou un booléen par soldat est requis.')
    if not nombre_1 or not nombre_2:
        return 0, 0
    fatigues_1, fatigues_2 = fatigues
    frais_1, frais_2 = nombre_1 - fatigues_1, nombre_2 - fatigues_2
    paires_fatiguees = min(fatigues_1, fatigues_2)
    bonus_1 = min(frais_1, fatigues_2 - paires_fatiguees)
    bonus_2 = min(frais_2, fatigues_1 - paires_fatiguees)
    frais_1 -= bonus_1
    frais_2 -= bonus_2
    paires_fraiches = min(frais_1, frais_2)
    return (bonus_1 + Fraction((frais_1 - paires_fraiches) * fatigues_2, nombre_2),
            bonus_2 + Fraction((frais_2 - paires_fraiches) * fatigues_1, nombre_1))


def combat_bloc(
    infos_1,
    infos_2,
    fatigue_1=False,
    fatigue_2=False,
    bloc_1=None,
    bloc_2=None,
    *,
    general_1=None,
    general_2=None,
):
    # Calcule le résultat d'un combat entre deux blocs.
    #
    # La fatigue accepte un booléen collectif ou les valeurs individuelles.
    # Les bonus collectifs précèdent les équivalents de frais avantagés.
    #
    # La fatigue ne modifie pas les avantages naturels
    # entre types différents.

    type_1 = infos_1["type"]
    type_2 = infos_2["type"]

    nombre_1 = infos_1["nombre"]
    nombre_2 = infos_2["nombre"]

    if nombre_1 == 0 or nombre_2 == 0:
        return nombre_1, nombre_2

    # Les soutiens isolés ne frappent pas et disparaissent avec leur bloc.
    soutien_1 = unites.etiquette(type_1, 'non_combattant')
    soutien_2 = unites.etiquette(type_2, 'non_combattant')
    if soutien_1 or soutien_2:
        return (0 if soutien_1 else nombre_1, 0 if soutien_2 else nombre_2)

    valeur_1 = valeur_base_bloc(infos_1, bloc_1) * multiplicateur(
        type_1,
        type_2, general_1, general_2
    )

    valeur_2 = valeur_base_bloc(infos_2, bloc_2) * multiplicateur(
        type_2,
        type_1, general_2, general_1
    )

    # ------------------------------------------
    # Fatigue
    # ------------------------------------------

    if type_1 == type_2:
        bonus_1, bonus_2 = bonus_fatigue(nombre_1, fatigue_1, nombre_2, fatigue_2)
        valeur_1 *= Fraction(nombre_1 + bonus_1, nombre_1)
        valeur_2 *= Fraction(nombre_2 + bonus_2, nombre_2)

    degats_1 = nombre_1 * valeur_1
    degats_2 = nombre_2 * valeur_2
    if 'sans_degats' in unites.definition(type_1)['effets']:
        degats_1 = 0
    if 'sans_degats' in unites.definition(type_2)['effets']:
        degats_2 = 0

    # Comme dans le moteur historique, la valeur effective sert aussi de
    # résistance : conserver les avantages et la fatigue au dénominateur.
    pertes_1 = min(nombre_1, degats_2 // valeur_1)
    pertes_2 = min(nombre_2, degats_1 // valeur_2)

    survivants_1 = max(
        0,
        nombre_1 - pertes_1
    )

    survivants_2 = max(
        0,
        nombre_2 - pertes_2
    )

    return survivants_1, survivants_2


def previsions_avant_muraille(contributions, infos_adverses, *, bloc_adverse,
                             general_adverse, fatigue_adverse=False):
    """Résultats numériques indépendants des Avant contre UN bloc explicite.

    Chaque contribution est (général d'origine, infos du bloc Avant, fatigue).
    Réutilise combat_bloc et les bonus du contexte courant, sans pertes réelles,
    tirages, blessures, XP, rapports ni mutations des entrées. L'ordre de sortie
    est celui des entrées : ce n'est PAS un classement d'efficacité.

    Préparation seulement : ces effectifs sont AVANT les sauvetages par moral
    et les capacités résolues hors combat_bloc (Bouclier vivant, Spore, etc.).
    Ni la cible, ni le score, ni la séquence des engagements ne sont choisis ici.
    Aucun appel depuis le combat réel tant que le contrat reste incomplet.
    """
    contributions = tuple(c for c in contributions
                          if progression.general_recoit_ordre(c[0], 'muraille_humaine'))
    ordres_calculs_v2.participants_muraille(
        ordres_pipeline.identite(general) for general, _, _ in contributions)
    # combat_bloc accepte déjà la fatigue collective ou individuelle.
    # Valider ici sans perdre l'information des soldats d'origine.
    def verifier_fatigue(fatigue, nombre):
        if type(fatigue) is bool:
            return
        if (isinstance(fatigue, (tuple, list)) and len(fatigue) == nombre
                and all(type(etat) is bool for etat in fatigue)):
            return
        raise ValueError('Fatigue : un booléen ou un booléen par soldat est requis.')

    verifier_fatigue(fatigue_adverse, infos_adverses['nombre'])
    for _, infos, fatigue in contributions:
        verifier_fatigue(fatigue, infos['nombre'])
    return tuple(dict(
        origine=ordres_pipeline.identite(general),
        survivants=combat_bloc(infos, infos_adverses, fatigue, fatigue_adverse,
                               'avant', bloc_adverse,
                               general_1=general, general_2=general_adverse),
    ) for general, infos, fatigue in contributions)


def simuler_avants_muraille(contributions, infos_adverses, *, general_adverse,
                           fatigue_adverse=False, aleatoire):
    """Prévisions Avant/Avant après moral, avec les contextes d'ordres fournis.

    Copie indépendante du générateur pour chaque candidat : ni le parcours
    des candidats ni cette simulation ne consomment les tirages du vrai combat.
    Les commandements et compositions restent ceux des généraux d'origine.
    Bouclier, Spore/Propagation et soutiens exigent encore leur simulateur :
    refus explicite plutôt qu'un classement ignorant leurs protections.
    Cette API préparatoire ne prépare pas les transmissions QG d'un duel.
    """
    from copy import deepcopy
    contributions = tuple(c for c in contributions
                          if progression.general_recoit_ordre(c[0], 'muraille_humaine'))
    for general in (general_adverse, *(g for g, _, _ in contributions)):
        composition = generaux.lire_composition_general(general['chemin'])
        if any(bloc.get('Trop_gros_zombie', 0) for bloc in composition.values()):
            raise NotImplementedError('Simulation Muraille : priorité du Bouclier hors Avant non raccordée.')
    for infos in (infos_adverses, *(i for _, i, _ in contributions)):
        if (infos.get('boucliers') or infos.get('soutiens') or
                infos['nombre'] and any(unites.etiquette(infos['type'], etiquette)
                    for etiquette in ('bouclier_vivant', 'propagation', 'non_combattant'))):
            raise NotImplementedError('Simulation Muraille : Bouclier, Spore/Propagation ou soutien non raccordé.')
    bruts = previsions_avant_muraille(contributions, infos_adverses,
        bloc_adverse='avant', general_adverse=general_adverse, fatigue_adverse=fatigue_adverse)
    resultat = []
    for (general, infos, _), brut in zip(contributions, bruts):
        hasard = deepcopy(aleatoire)
        propres = soldats.prevoir_pertes(infos, brut['survivants'][0],
                                         moral_des_pertes(infos, general), hasard)
        adverses = soldats.prevoir_pertes(infos_adverses, brut['survivants'][1],
            moral_des_pertes(infos_adverses, general_adverse), hasard)
        pertes_alliees, elimines = len(propres['pertes']), len(adverses['pertes'])
        resultat.append(dict(origine=brut['origine'], allies=propres, adverses=adverses,
            allies_perdus=pertes_alliees, ennemis_elimines=elimines,
            score=elimines - pertes_alliees))
    return tuple(resultat)


def prochain_avant_muraille(generaux_allies, general_adverse, *, aleatoire,
                            qg_nommade=None, reserve_strategique=None):
    """Relit les forces restantes et recalcule le meilleur Avant à chaque appel.

    Aucune liste de classement figée, aucun engagement réel. Les exclusions
    sont des identités officielles de rôles déjà retenus par le pilote.
    Celui-ci devra encore préparer les contextes des ordres par confrontation.
    """
    from copy import deepcopy
    generaux_allies = tuple(g for g in generaux_allies
                           if progression.general_recoit_ordre(g, 'muraille_humaine'))
    admis = ordres_calculs_v2.participants_muraille(
        (ordres_pipeline.identite(g) for g in generaux_allies), qg_nommade, reserve_strategique)
    contributions, positions = [], {}
    for general in generaux_allies:
        identite = ordres_pipeline.identite(general)
        if identite not in admis:
            continue
        infos = generaux.lire_blocs_general(general['chemin'], lecture_seule=True)['avant']
        if infos['nombre']:
            contributions.append((general, infos, etat.general_est_fatigue(general)))
            positions[identite] = general['emplacement']
    adverse = generaux.lire_blocs_general(general_adverse['chemin'], lecture_seule=True)['avant']
    if not adverse['nombre']:
        return dict(choisi=None, previsions=())
    previsions = simuler_avants_muraille(contributions, adverse,
        general_adverse=general_adverse, fatigue_adverse=etat.general_est_fatigue(general_adverse),
        aleatoire=aleatoire)
    choisi = ordres_calculs_v2.choisir_avant_muraille(
        {p['origine']: p['score'] for p in previsions}, positions, deepcopy(aleatoire))
    return dict(choisi=choisi, previsions=previsions)




def engager_avant_muraille(general_allie, general_adverse, *, participants=None,
                           generaux_muraille=None, aleatoire=None):
    """Résout un choc Avant/Avant de Muraille avec le moteur réel existant.

    Pertes, moral, blessures, XP et effets après confrontation suivent
    confrontation_directe -> resoudre_blocs, sans deuxième formule de combat.
    Le pilote du territoire reste responsable des transmissions QG et des
    priorités précédant le choc (dont Bouclier vivant). Aucun effet d'ordre
    global n'est activé par ce raccordement seul.
    """
    if general_allie['joueur'] == general_adverse['joueur']:
        raise ValueError('Muraille exige deux joueurs adversaires.')
    if (general_allie.get('camp', general_allie['joueur']) ==
            general_adverse.get('camp', general_adverse['joueur'])):
        raise ValueError('Muraille exige deux camps adversaires.')
    if (bouclier_vivant.presence_bouclier(general_allie)
            or bouclier_vivant.presence_bouclier(general_adverse)):
        raise NotImplementedError(
            'Muraille : priorité du Bouclier vivant avant le choc non raccordée.')
    participants = participants if participants is not None else soldats.VueParticipants()
    participants.verifier_duel(general_allie, general_adverse)
    armee = {
        general_allie['joueur']: participants.blocs(general_allie),
        general_adverse['joueur']: participants.blocs(general_adverse),
    }
    if generaux_muraille is None:
        return confrontation_directe(
            armee, general_allie, general_adverse, 'avant', participants=participants)

    # Le calcul des dégâts reste celui des deux blocs réellement opposés.
    # Seule la répartition des pertes subies par le camp Muraille est collective.
    # Chaque soldat reste sur son bloc et garde le moral de son général.
    aleatoire = random if aleatoire is None else aleatoire
    membres = tuple(generaux_muraille)
    identites = [ordres_pipeline.identite(g) for g in membres]
    engage = ordres_pipeline.identite(general_allie)
    if engage not in identites or len(identites) != len(set(identites)):
        raise ValueError('Le général engagé doit appartenir une seule fois à Muraille.')
    if any(g.get('camp', g['joueur']) != general_allie.get('camp', general_allie['joueur'])
           for g in membres):
        raise ValueError('Muraille ne peut réunir deux camps.')
    blocs = {ordres_pipeline.identite(g): participants.blocs(g)['avant'] for g in membres}
    if any(b.get('boucliers') or b.get('soutiens') or
           (b['nombre'] and any(unites.etiquette(b['type'], e)
            for e in ('bouclier_vivant', 'propagation', 'non_combattant')))
           for b in blocs.values()):
        raise NotImplementedError('Muraille : capacités spéciales collectives non raccordées.')
    for g in membres:
        if bouclier_vivant.presence_bouclier(g):
            raise NotImplementedError('Muraille : priorité Bouclier non raccordée.')
    actif = blocs[engage]
    adverse = armee[general_adverse['joueur']]['avant']
    if not actif['nombre'] or not adverse['nombre']:
        return None
    fatigue_1 = participants.fatigue(general_allie, actif)
    fatigue_2 = participants.fatigue(general_adverse, adverse)
    initial_allie, initial_adverse = actif['nombre'], adverse['nombre']
    survivants_1, survivants_2 = combat_bloc(
        actif, adverse, fatigue_1, fatigue_2, 'avant', 'avant',
        general_1=general_allie, general_2=general_adverse)
    soldats.affrontement(general_allie, general_adverse)
    nombre_pertes = actif['nombre'] - survivants_1
    selection = soldats.repartir_victimes_muraille(
        blocs, nombre_pertes, engage, aleatoire)
    moraux = {ordres_pipeline.identite(g): moral_des_pertes(
        blocs[ordres_pipeline.identite(g)], g, participants=participants)
        for g in membres}
    pertes_collectives = soldats.appliquer_victimes_muraille(
        blocs, selection, moraux, aleatoire)
    ordres_pipeline.verifier_qg()
    pertes_adverses = supprimer_unites(
        adverse, survivants_2, general_adverse, participants=participants)
    pertes_alliees = [p for groupe in pertes_collectives.values() for p in groupe]
    unites.apres_confrontation(general_allie, general_adverse,
                              'avant', 'avant', actif, adverse,
                              pertes_alliees, pertes_adverses)
    for g in membres:
        if g['chemin'].exists():
            generaux.supprimer_general_si_vide(g)
    if general_adverse['chemin'].exists():
        generaux.supprimer_general_si_vide(general_adverse)
    return dict(moment='Choc', bloc_1='avant', bloc_2='avant',
                initial_1=initial_allie, initial_2=initial_adverse,
                final_1=actif['nombre'], final_2=adverse['nombre'],
                pertes_collectives=pertes_collectives)


def enchainer_avants_muraille(generaux_allies, general_adverse, *, aleatoire,
                             engager=None, qg_nommade=None, reserve_strategique=None,
                             transmission_active=None, camp=None):
    """Sélection successive des Avant de Muraille, sans classement figé.

    Après chaque engagement, relit les blocs restants via prochain_avant_muraille.
    `engager(general)` est le raccordement au combat réel, fourni par le pilote :
    il doit résoudre UN choc et appliquer ses pertes avant de rendre la main.
    Cette fonction ne déclenche pas encore Muraille dans la bataille normale.
    Un général ne fournit son Avant qu'une fois par choc initial.
    Le pilote peut fournir transmission_active() : le QG est alors vérifié
    entre les chocs, jamais pendant celui déjà engagé.
    """
    if engager is None:
        engager = lambda general: engager_avant_muraille(
            general, general_adverse, generaux_muraille=tuple(
                g for g in generaux_allies
                if g.get('chemin') is None or g['chemin'].exists()),
            aleatoire=aleatoire)
    if not callable(engager):
        raise TypeError('Le pilote doit fournir une fonction engager.')
    if camp is not None:
        if transmission_active is not None:
            raise ValueError('Choisir le QG territorial ou une vérification injectée.')
        transmission_active = lambda: ordres_pipeline.transmission_muraille_active(camp)
    if transmission_active is not None and not callable(transmission_active):
        raise TypeError('La vérification du QG doit être une fonction.')
    disponibles = tuple(generaux_allies)
    identites = [ordres_pipeline.identite(g) for g in disponibles]
    if len(set(identites)) != len(identites):
        raise ValueError('Un général ne peut contribuer deux fois à Muraille.')
    engagements = []
    while disponibles:
        if transmission_active is not None and not transmission_active():
            break
        decision = prochain_avant_muraille(
            disponibles, general_adverse, aleatoire=aleatoire,
            qg_nommade=qg_nommade, reserve_strategique=reserve_strategique)
        identite = decision['choisi']
        if identite is None:
            break
        choisi = next(g for g in disponibles if ordres_pipeline.identite(g) == identite)
        engagements.append((identite, engager(choisi)))
        disponibles = tuple(g for g in disponibles
                            if ordres_pipeline.identite(g) != identite)
    return tuple(engagements)


def trouver_cible_facile(armee, joueur_attaquant, type_attaquant,
                         general_attaquant=None, general_defenseur=None):
    joueur_ennemi = adversaire_du_duel(armee, joueur_attaquant)

    for bloc in config.ordre_blocs:
        infos_ennemi = armee[joueur_ennemi][bloc]

        if multiplicateur(type_attaquant, infos_ennemi['type'], general_attaquant,
                          general_defenseur) > 1 and infos_ennemi["nombre"] > 0:
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


def moral_des_pertes(infos, general=None, *, participants=None):
    """Lecture commune au combat et aux prévisions, sans mutation persistante."""
    caracteristiques = progression.caracteristiques_general(general) if general else None
    moral = 0
    if caracteristiques and general['chemin'].is_dir():
        if caracteristiques['nature'] == 'stratege':
            caracteristiques['moral'] = 0
        composition = (participants.composition(general) if participants is not None
                       else generaux.lire_composition_general(general['chemin']))
        bloc = infos['unites'][0].parent.name if infos['unites'] else None
        moral = unites.moral_bloc(caracteristiques, composition, bloc, general)
        moral = ordres_pipeline.moral(general, moral, type_unite=infos['type'])
    return moral


def supprimer_unites(infos, survivants, general=None, *, participants=None,
                    unites_prioritaires=()):
    if participants is not None and participants.groupe:
        participants.groupe.bilan()
    pertes = soldats.pertes(infos, survivants,
                           moral_des_pertes(infos, general, participants=participants), random,
                           unites_prioritaires=unites_prioritaires)
    ordres_pipeline.verifier_qg()
    if participants is not None and participants.groupe:
        participants.groupe.bilan()
    return pertes


def resoudre_blocs(infos_1, infos_2, general_1, general_2, bloc_1, bloc_2,
                   fatigue_1, fatigue_2, *, participants=None,
                   prioritaires_1=(), prioritaires_2=()):
    """Résolution commune du choc et de la manœuvre, dans leur ordre historique.

    Les deux dégâts sont calculés avant les pertes ; les sauvetages puis les
    capacités gardent leur séquence et leurs tirages. La phase fait son rapport.
    """
    survivants_1, survivants_2 = combat_bloc(
        infos_1, infos_2, fatigue_1, fatigue_2, bloc_1, bloc_2,
        general_1=general_1, general_2=general_2)
    if infos_1['nombre'] > 0 and infos_2['nombre'] > 0:
        soldats.affrontement(general_1, general_2)
    pertes_1 = supprimer_unites(infos_1, survivants_1, general_1,
                               participants=participants, unites_prioritaires=prioritaires_1)
    pertes_2 = supprimer_unites(infos_2, survivants_2, general_2,
                               participants=participants, unites_prioritaires=prioritaires_2)
    unites.apres_confrontation(general_1, general_2, bloc_1, bloc_2,
                              infos_1, infos_2, pertes_1, pertes_2)
    return pertes_1, pertes_2


def afficher_fatigue(nom, fatigue):
    """Le texte historique reste inchangé pour les blocs homogènes."""
    if isinstance(fatigue, (tuple, list)):
        rapports.afficher_et_ecrire(
            f'{nom} : FATIGUE PARTIELLE ({sum(fatigue)}/{len(fatigue)} soldats)')
    elif fatigue:
        rapports.afficher_et_ecrire(f'{nom} : FATIGUÉ')


def confrontation_directe(
    armee,
    general_1,
    general_2,
    bloc, *, participants=None
):
    # Résout le choc initial entre deux blocs placés face à face.
    # Retourne aussi les données structurées utilisées par le rapport de bataille.

    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    nom_1 = f"{joueur_1} {rapports.nom_affichage_general(general_1)}"
    nom_2 = f"{joueur_2} {rapports.nom_affichage_general(general_2)}"

    participants = participants if participants is not None else soldats.VueParticipants()
    infos_1 = participants.blocs(general_1)[bloc] if participants.groupe else armee[joueur_1][bloc]
    infos_2 = participants.blocs(general_2)[bloc] if participants.groupe else armee[joueur_2][bloc]

    if infos_1["nombre"] == 0 or infos_2["nombre"] == 0:
        return None

    initial_1 = infos_1["nombre"]
    initial_2 = infos_2["nombre"]
    type_1 = infos_1["type"]
    type_2 = infos_2["type"]

    fatigue_1 = participants.fatigue(general_1, infos_1)
    fatigue_2 = participants.fatigue(general_2, infos_2)

    rapports.afficher_et_ecrire("\n" + "-" * 60)
    rapports.afficher_et_ecrire(f"Choc initial : {bloc}")
    rapports.afficher_et_ecrire("")

    afficher_fatigue(nom_1, fatigue_1)
    afficher_fatigue(nom_2, fatigue_2)

    rapports.afficher_et_ecrire(f"{nom_1} : {rapports.formater_force(infos_1)}")
    rapports.afficher_et_ecrire(f"{nom_2} : {rapports.formater_force(infos_2)}")

    pertes_1, pertes_2 = resoudre_blocs(
        infos_1, infos_2, general_1, general_2, bloc, bloc,
        fatigue_1, fatigue_2, participants=participants)
    survivants_1, survivants_2 = infos_1['nombre'], infos_2['nombre']

    rapports.afficher_et_ecrire("\nRésultat :")
    rapports.afficher_et_ecrire(
        f"{nom_1} : {rapports.formater_survivants(survivants_1, type_1)}"
    )
    rapports.afficher_et_ecrire(
        f"{nom_2} : {rapports.formater_survivants(survivants_2, type_2)}"
    )

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


def phase_engagement_initial(general_1, general_2, *, participants=None):
    participants = participants if participants is not None else soldats.VueParticipants()
    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    rapports.afficher_et_ecrire("\n=== CHOC INITIAL ===")

    armee_depart = {
        joueur_1: participants.blocs(general_1),
        joueur_2: participants.blocs(general_2),
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
            f"{joueur_1} {rapports.nom_affichage_general(general_1)} {rapports.formater_force(infos_1)} "
            f"VS "
            f"{joueur_2} {rapports.nom_affichage_general(general_2)} {rapports.formater_force(infos_2)}"
        )

    rapports.afficher_et_ecrire("\n--- Résolution du choc initial ---")

    for bloc in combats_prevus:
        if not participants.present(general_1) or not participants.present(general_2):
            break

        armee = {
            joueur_1: participants.blocs(general_1),
            joueur_2: participants.blocs(general_2),
        }

        detail = confrontation_directe(
            armee,
            general_1,
            general_2,
            bloc, participants=participants
        )

        if detail is not None:
            details_choc.append(detail)

        if participants.present(general_1):
            participants.supprimer_general_si_vide(general_1)

        if participants.present(general_2):
            participants.supprimer_general_si_vide(general_2)

    return initiative_avant, details_choc


def attaque_ciblee(
    armee,
    general_attaquant,
    general_defenseur,
    bloc_attaquant,
    bloc_cible, *, participants=None
):
    # Résout une manœuvre contre un bloc ennemi.
    # Retourne les données nécessaires au rapport de bataille.

    joueur_attaquant = general_attaquant["joueur"]
    joueur_ennemi = general_defenseur["joueur"]

    nom_attaquant = f"{joueur_attaquant} {rapports.nom_affichage_general(general_attaquant)}"
    nom_defenseur = f"{joueur_ennemi} {rapports.nom_affichage_general(general_defenseur)}"

    participants = participants if participants is not None else soldats.VueParticipants()
    infos_attaquant = (participants.blocs(general_attaquant)[bloc_attaquant] if participants.groupe
                       else armee[joueur_attaquant][bloc_attaquant])
    infos_defenseur = (participants.blocs(general_defenseur)[bloc_cible] if participants.groupe
                       else armee[joueur_ennemi][bloc_cible])

    initial_attaquant = infos_attaquant["nombre"]
    initial_defenseur = infos_defenseur["nombre"]
    type_attaquant = infos_attaquant["type"]
    type_defenseur = infos_defenseur["type"]

    fatigue_attaquant = participants.fatigue(general_attaquant, infos_attaquant)
    fatigue_defenseur = participants.fatigue(general_defenseur, infos_defenseur)

    rapports.afficher_et_ecrire("\n" + "-" * 60)
    rapports.afficher_et_ecrire("Manœuvre")
    rapports.afficher_et_ecrire("")

    rapports.afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} "
        f"attaque {nom_defenseur} {bloc_cible}"
    )

    afficher_fatigue(nom_attaquant, fatigue_attaquant)
    afficher_fatigue(nom_defenseur, fatigue_defenseur)

    rapports.afficher_et_ecrire("\nForces engagées :")
    rapports.afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} : {rapports.formater_force(infos_attaquant)}"
    )
    rapports.afficher_et_ecrire(
        f"{nom_defenseur} {bloc_cible} : {rapports.formater_force(infos_defenseur)}"
    )

    pertes_attaquant, pertes_defenseur = resoudre_blocs(
        infos_attaquant, infos_defenseur, general_attaquant, general_defenseur,
        bloc_attaquant, bloc_cible, fatigue_attaquant, fatigue_defenseur,
        participants=participants)
    survivants_attaquant, survivants_defenseur = infos_attaquant['nombre'], infos_defenseur['nombre']

    rapports.afficher_et_ecrire("\nRésultat :")
    rapports.afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} : "
        f"{rapports.formater_survivants(survivants_attaquant, type_attaquant)}"
    )
    rapports.afficher_et_ecrire(
        f"{nom_defenseur} {bloc_cible} : "
        f"{rapports.formater_survivants(survivants_defenseur, type_defenseur)}"
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


def choisir_cible(armee, joueur_attaquant, type_attaquant,
                  general_attaquant=None, general_defenseur=None):
    joueur_ennemi = adversaire_du_duel(armee, joueur_attaquant)

    cible = trouver_cible_facile(armee, joueur_attaquant, type_attaquant,
                                general_attaquant, general_defenseur)

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
