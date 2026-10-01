"""Sélection du mode et résolution d'un tour classique de Mythodea."""
import argparse
import json

import config


def resoudre_tour_classique():
    # Les imports Unix restent réservés à l'exécution réelle du moteur.
    import generaux
    import plateau
    import rapports
    import securite
    import victoire

    rapports.preparer_rapports()
    plateau.reparer_structure()

    # Une seule génération par joueur, au même moment du tour qu'en V1.5.
    # Réparer le plateau séparément ne doit plus créer de généraux.
    for joueur in config.joueurs:
        generaux.faire_apparaitre_general_si_possible(joueur)

    securite.verifier_tous_les_deplacements()

    vainqueur = victoire.verifier_victoire()

    if vainqueur:
        rapports.ecrire_rapport_court("")

        rapports.ecrire_rapport_court(
            f"VICTOIRE DE {vainqueur}"
        )

        rapports.ecrire_rapport_long(
            f"Victoire de {vainqueur}."
        )

    else:
        plateau.lancer_bataille_v15()

    rapports.afficher_fin_de_tour()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mythodea : sélection du mode de jeu")
    parser.add_argument("--mode", choices=config.modes_disponibles, default="classique")
    parser.add_argument(
        "--afficher-configuration", action="store_true",
        help="afficher le profil sélectionné sans lancer de tour ni modifier le plateau",
    )
    arguments = parser.parse_args(argv)
    configuration = config.configuration_mode(arguments.mode)

    if arguments.afficher_configuration:
        print(json.dumps(configuration, ensure_ascii=False, indent=2, default=str))
        return

    if arguments.mode == "survie":
        parser.error(
            "Le mode Survie Est dispose de sa configuration mais n'est pas encore jouable. "
            "Utilisez --mode survie --afficher-configuration pour la consulter."
        )

    resoudre_tour_classique()


if __name__ == "__main__":
    main()
