"""Lecture et écriture des états persistants, fatigue et météo."""
import random
import os
import json
from contextlib import contextmanager

import config


@contextmanager
def verrou_cycle_survie(configuration):
    """Exclut deux pilotes/résolveurs concurrents, y compris pendant le timer."""
    chemin = configuration["game_path"] / "systeme/verrou_cycle_survie"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as erreur:
        raise RuntimeError("Cycle Survie déjà verrouillé ; vérifier le processus avant toute reprise.") from erreur
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as fichier:
            os.chown(chemin, 0, 0)
            os.chmod(chemin, 0o600)
            fichier.write(f"{os.getpid()}\n")
        yield
    finally:
        chemin.unlink()


def charger_cycle_survie(configuration):
    chemin = configuration["game_path"] / "systeme/cycle_survie.json"
    if not chemin.exists():
        return None
    cycle = json.loads(chemin.read_text(encoding="utf-8"))
    if (type(cycle.get("tour")) is not int or cycle["tour"] < 0
            or cycle.get("phase") not in ("preparation", "actions", "resolution", "a_preparer", "defaite")):
        raise ValueError("État du cycle Survie invalide.")
    return cycle


def sauvegarder_cycle_survie(cycle, configuration):
    """État privé remplacé atomiquement ; le numéro de vague vaut toujours tour+1."""
    chemin = configuration["game_path"] / "systeme/cycle_survie.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(".tmp")
    # Créer privé avant l'écriture, même si le umask du processus est permissif.
    descriptor = os.open(temporaire, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as fichier:
        os.chown(temporaire, 0, 0)
        os.chmod(temporaire, 0o600)
        json.dump(cycle, fichier, ensure_ascii=False)
        fichier.write("\n")
    temporaire.replace(chemin)


def charger_attentes_repli(configuration=None):
    racine = config.game_path if configuration is None else configuration["game_path"]
    chemin = racine / "systeme" / "attente_repli.txt"
    if not chemin.exists():
        return {}
    attentes = {}
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        identifiant, valeur = ligne.split("=", 1)
        if not valeur.isascii() or not valeur.isdecimal():
            raise ValueError(f"Délai de repli invalide : {ligne}")
        if int(valeur):
            attentes[identifiant] = int(valeur)
    return attentes


def sauvegarder_attentes_repli(attentes, configuration=None):
    """Compteurs privés du moteur, indépendants des fichiers des joueurs."""
    racine = config.game_path if configuration is None else configuration["game_path"]
    chemin = racine / "systeme" / "attente_repli.txt"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("".join(f"{cle}={attentes[cle]}\n" for cle in sorted(attentes)
                               if attentes[cle] > 0), encoding="utf-8")
    os.chown(chemin, 0, 0)
    os.chmod(chemin, 0o600)


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


def charger_controle_territoires(configuration=None):
    # Charge le contrôle des territoires au tour précédent.
    #
    # Exemple du fichier :
    # base1=j1
    # terrain1=neutre
    # terrain2=j2

    controle = {}

    # Par défaut, tous les territoires sont neutres.
    territoires = config.territoires if configuration is None else configuration["territoires"]
    for territory in territoires:
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
