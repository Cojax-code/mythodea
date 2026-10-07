"""Sélection du mode et résolution d'un tour classique de Mythodea."""
import argparse
import json

import config


def lancer_survie(configuration, nombre_tours=None):
    import survie
    return survie.lancer_partie_survie(configuration, nombre_tours)


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
    parser.add_argument("--duree-action", type=float, default=None,
                        help="durée d'action Survie en secondes (défaut : 120, 0 sans attente)")
    parser.add_argument("--tours", type=int, default=None,
                        help="arrêter après ce nombre de résolutions Survie")
    parser.add_argument('--duree-consultation', type=float, default=None,
                        help='consultation en secondes (défaut : 60)')
    parser.add_argument('--duree-gel', type=float, default=None,
                        help='gel minimum de capture (défaut : 10)')
    parser.add_argument('--seuil-capture', type=float, default=None,
                        help='seuil de sécurité de capture, provisoirement 120 secondes')
    parser.add_argument(
        "--afficher-configuration", action="store_true",
        help="afficher le profil sélectionné sans lancer de tour ni modifier le plateau",
    )
    arguments = parser.parse_args(argv)
    configuration = config.configuration_mode(arguments.mode)
    for option, cle in ((arguments.duree_consultation, 'duree_consultation_secondes'),
                        (arguments.duree_gel, 'duree_gel_secondes'),
                        (arguments.seuil_capture, 'seuil_capture_secondes')):
        if option is not None:
            if arguments.mode != 'survie':
                parser.error('Les durées de phase sont réservées au mode Survie.')
            import minuterie
            try:
                configuration[cle] = minuterie.valider_duree(option)
            except ValueError as erreur:
                parser.error(str(erreur))
    if configuration['seuil_capture_secondes'] <= configuration['duree_gel_secondes']:
        parser.error('Le seuil de capture doit dépasser le gel minimum.')
    if arguments.duree_action is not None:
        import minuterie
        try:
            configuration["duree_phase_action_secondes"] = minuterie.valider_duree(arguments.duree_action)
        except ValueError as erreur:
            parser.error(str(erreur))
    if arguments.tours is not None and arguments.tours < 1:
        parser.error("--tours doit être positif")
    if arguments.mode != "survie" and (arguments.duree_action is not None or arguments.tours is not None):
        parser.error("--duree-action et --tours sont réservés au mode Survie")

    if arguments.afficher_configuration:
        print(json.dumps(configuration, ensure_ascii=False, indent=2, default=str))
        return

    if arguments.mode == "survie":
        lancer_survie(configuration, arguments.tours)
        return

    resoudre_tour_classique()


if __name__ == "__main__":
    main()
