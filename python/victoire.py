"""Lecture des objectifs et vérification des tentatives de victoire."""
import config
import rapports


def lire_fichier(chemin):
    if chemin.exists():
        return chemin.read_text().strip()
    return ""


def vider_fichier(chemin):
    chemin.write_text("", encoding="utf-8")


def verifier_victoire():
    objectif_base1 = lire_fichier(config.game_path / "base1" / "objectif.txt")
    objectif_base2 = lire_fichier(config.game_path / "base2" / "objectif.txt")

    tentative_j1 = lire_fichier(config.game_path / "base2" / "tentative_j1.txt")
    tentative_j2 = lire_fichier(config.game_path / "base1" / "tentative_j2.txt")

    if tentative_j1 == objectif_base2 and tentative_j1 != "":
        return "j1"

    if tentative_j2 == objectif_base1 and tentative_j2 != "":
        return "j2"

    if tentative_j1 != "":
        rapports.afficher_et_ecrire("Tentative de victoire de j1 échouée")
        vider_fichier(config.game_path / "base2" / "tentative_j1.txt")

    if tentative_j2 != "":
        rapports.afficher_et_ecrire("Tentative de victoire de j2 échouée")
        vider_fichier(config.game_path / "base1" / "tentative_j2.txt")

    return None
