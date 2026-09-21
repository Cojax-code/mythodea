"""Lecture et écriture des états persistants, fatigue et météo."""
import random

import config


def lire_compteur_general(joueur):
    # Lit le compteur de génération des généraux.
    #
    # Exemple :
    # /home/game/systeme/compteur_general_j1.txt contient 2
    # donc le prochain général sera general3.

    compteur_path = config.game_path / "systeme" / f"compteur_general_{joueur}.txt"

    if not compteur_path.exists():
        return 0

    texte = compteur_path.read_text(encoding="utf-8").strip()

    if texte == "":
        return 0

    return int(texte)


def sauvegarder_compteur_general(joueur, numero):
    # Sauvegarde le dernier numéro de général créé.

    compteur_path = config.game_path / "systeme" / f"compteur_general_{joueur}.txt"
    compteur_path.parent.mkdir(exist_ok=True)
    compteur_path.write_text(str(numero), encoding="utf-8")


def charger_controle_territoires():
    # Charge le contrôle des territoires au tour précédent.
    #
    # Exemple du fichier :
    # base1=j1
    # terrain1=neutre
    # terrain2=j2

    controle = {}

    # Par défaut, tous les territoires sont neutres.
    for territory in config.territoires:
        controle[territory.name] = "neutre"

    if not config.controle_territoires_path.exists():
        return controle

    lignes = config.controle_territoires_path.read_text(encoding="utf-8").splitlines()

    for ligne in lignes:
        if "=" not in ligne:
            continue

        nom_territoire, valeur = ligne.split("=", 1)
        controle[nom_territoire.strip()] = valeur.strip()

    return controle


def charger_positions_generaux():
    positions = {}

    if not config.positions_generaux_path.exists():
        return positions

    lignes = config.positions_generaux_path.read_text(
        encoding="utf-8"
    ).splitlines()

    for ligne in lignes:
        if "=" not in ligne:
            continue

        identifiant, position = ligne.split("=", 1)
        positions[identifiant.strip()] = position.strip()

    return positions


def sauvegarder_positions_generaux(positions):
    lignes = []

    for identifiant in sorted(positions):
        lignes.append(
            f"{identifiant}={positions[identifiant]}"
        )

    config.positions_generaux_path.parent.mkdir(exist_ok=True)

    config.positions_generaux_path.write_text(
        "\n".join(lignes),
        encoding="utf-8"
    )


def enregistrer_position_nouveau_general(joueur, nom_general):
    positions = charger_positions_generaux()

    identifiant = f"{joueur}:{nom_general}"
    positions[identifiant] = "home"

    sauvegarder_positions_generaux(positions)


def sauvegarder_generaux_fatigues(generaux_fatigues):
    config.fatigue_generaux_path.parent.mkdir(exist_ok=True)

    config.fatigue_generaux_path.write_text(
        "\n".join(sorted(generaux_fatigues)),
        encoding="utf-8"
    )


def charger_generaux_fatigues():
    if not config.fatigue_generaux_path.exists():
        return set()

    return set(
        ligne.strip()
        for ligne in config.fatigue_generaux_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if ligne.strip()
    )


def general_est_fatigue(general):
    # Vérifie si un général est fatigué à cause
    # d'une marche forcée effectuée pendant ce tour.

    generaux_fatigues = charger_generaux_fatigues()

    identifiant = (
        f"{general['joueur']}:{general['nom']}"
    )

    return identifiant in generaux_fatigues


def choisir_meteo_tour():
    # Choisit une météo aléatoire.
    #
    # La météo est commune à toute la carte
    # et n'a encore aucun effet sur le jeu.

    return random.choice(
        config.meteos_possibles
    )


def sauvegarder_meteo(meteo):
    # Conserve la météo du tour dans le système.

    config.meteo_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    config.meteo_path.write_text(
        meteo,
        encoding="utf-8"
    )


def charger_meteo():
    # Permet aux futures fonctions du jeu
    # de consulter la météo choisie.

    if not config.meteo_path.exists():
        return None

    meteo = config.meteo_path.read_text(
        encoding="utf-8"
    ).strip()

    if meteo == "":
        return None

    return meteo
