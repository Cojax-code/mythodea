"""Point d’entrée : résolution d’un tour de Mythodea V1.5."""
import plateau
import rapports
import securite
import victoire


def main():
    rapports.preparer_rapports()
    plateau.reparer_structure()

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


if __name__ == "__main__":
    main()
