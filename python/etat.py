"""Lecture et écriture des états persistants, fatigue et météo."""
import random
import os
import json
import stat
from contextlib import contextmanager

import config


def ecrire_prive(chemin, texte):
    """Remplacement atomique et durable d'un état root:root 600."""
    for parent in (chemin, *chemin.parents):
        if parent.is_symlink():
            raise RuntimeError(f"Lien interdit pour un état moteur : {parent}")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix('.tmp')
    if temporaire.exists() or temporaire.is_symlink():
        infos = temporaire.lstat()
        if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1 or infos.st_uid != 0:
            raise RuntimeError(f"Fichier temporaire non sûr : {temporaire}")
    fd = os.open(temporaire, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as fichier:
        os.chown(temporaire, 0, 0)
        os.chmod(temporaire, 0o600)
        fichier.write(texte)
        fichier.flush()
        os.fsync(fichier.fileno())
    temporaire.replace(chemin)
    if os.name == 'posix':
        fd = os.open(chemin.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


@contextmanager
def verrou_cycle_survie(configuration):
    """Exclut deux pilotes/résolveurs concurrents, y compris pendant le timer."""
    chemin = configuration["game_path"] / "systeme/verrou_cycle_survie"
    for parent in (chemin.parent, *chemin.parent.parents):
        if parent.is_symlink():
            raise RuntimeError(f"Parent du verrou non sûr : {parent}")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    os.chown(chemin.parent, 0, 0)
    os.chmod(chemin.parent, 0o700)
    try:
        descriptor = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as erreur:
        raise RuntimeError("Cycle Survie déjà verrouillé ; vérifier le processus avant toute reprise.") from erreur
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as fichier:
            os.chown(chemin, 0, 0)
            os.chmod(chemin, 0o600)
            fichier.write(f"{os.getpid()}\n")
            fichier.flush()
            os.fsync(fichier.fileno())
        yield
    finally:
        chemin.unlink()


def charger_cycle_survie(configuration):
    chemin = configuration["game_path"] / "systeme/cycle_survie.json"
    if not chemin.exists():
        return None
    cycle = json.loads(chemin.read_text(encoding="utf-8"))
    if (type(cycle.get("tour")) is not int or cycle["tour"] < 0
            or cycle.get("phase") not in ("preparation", "actions", "capture", "resolution", "publication", "consultation", "recuperation", "a_preparer", "defaite")):
        raise ValueError("État du cycle Survie invalide.")
    return cycle


def sauvegarder_cycle_survie(cycle, configuration):
    """État privé remplacé atomiquement ; le numéro de vague vaut toujours tour+1."""
    chemin = configuration["game_path"] / "systeme/cycle_survie.json"
    ecrire_prive(chemin, json.dumps(cycle, ensure_ascii=False) + '\n')


def charger_attentes_repli(configuration=None):
    racine = config.racine_metier() if configuration is None else configuration["game_path"]
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
    racine = config.racine_metier() if configuration is None else configuration["game_path"]
    chemin = racine / "systeme" / "attente_repli.txt"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    ecrire_prive(chemin, "".join(f"{cle}={attentes[cle]}\n" for cle in sorted(attentes)
                               if attentes[cle] > 0))


def lire_compteur_general(joueur):
    # Lit le compteur de génération des généraux.
    #
    # Exemple :
    # /home/game/systeme/compteur_general_j1.txt contient 2
    # donc le prochain général sera general3.

    compteur_path = config.racine_metier() / "systeme" / f"compteur_general_{joueur}.txt"

    if not compteur_path.exists():
        return 0

    texte = compteur_path.read_text(encoding="utf-8").strip()

    if texte == "":
        return 0

    return int(texte)


def sauvegarder_compteur_general(joueur, numero):
    # Sauvegarde le dernier numéro de général créé.

    compteur_path = config.racine_metier() / "systeme" / f"compteur_general_{joueur}.txt"
    compteur_path.parent.mkdir(exist_ok=True)
    ecrire_prive(compteur_path, str(numero))


def initialiser_quota_normal(joueur):
    chemin = config.racine_metier() / 'systeme' / f'compteur_creation_normale_{joueur}.txt'
    if not chemin.exists():
        # Migration : avant la Crypte, tous les numéros étaient des créations normales.
        ecrire_prive(chemin, str(lire_compteur_general(joueur)))
    return int(chemin.read_text(encoding='utf-8'))


def sauvegarder_quota_normal(joueur, nombre):
    ecrire_prive(config.racine_metier() / 'systeme' / f'compteur_creation_normale_{joueur}.txt', str(nombre))


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

    if not config.chemin_etat("controle_territoires_path").exists():
        return controle

    lignes = config.chemin_etat("controle_territoires_path").read_text(encoding="utf-8").splitlines()

    for ligne in lignes:
        if "=" not in ligne:
            continue

        nom_territoire, valeur = ligne.split("=", 1)
        controle[nom_territoire.strip()] = valeur.strip()

    return controle


def charger_positions_generaux():
    positions = {}

    if not config.chemin_etat("positions_generaux_path").exists():
        return positions

    lignes = config.chemin_etat("positions_generaux_path").read_text(
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

    config.chemin_etat("positions_generaux_path").parent.mkdir(exist_ok=True)

    ecrire_prive(config.chemin_etat("positions_generaux_path"), "\n".join(lignes))


def enregistrer_position_nouveau_general(joueur, nom_general):
    positions = charger_positions_generaux()

    identifiant = f"{joueur}:{nom_general}"
    positions[identifiant] = "home"

    sauvegarder_positions_generaux(positions)


def sauvegarder_generaux_fatigues(generaux_fatigues):
    config.chemin_etat("fatigue_generaux_path").parent.mkdir(exist_ok=True)

    ecrire_prive(config.chemin_etat("fatigue_generaux_path"), "\n".join(sorted(generaux_fatigues)))


def charger_generaux_fatigues():
    if not config.chemin_etat("fatigue_generaux_path").exists():
        return set()

    return set(
        ligne.strip()
        for ligne in config.chemin_etat("fatigue_generaux_path").read_text(
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

    config.chemin_etat("meteo_path").parent.mkdir(
        parents=True,
        exist_ok=True
    )

    ecrire_prive(config.chemin_etat("meteo_path"), meteo)


def charger_meteo():
    # Permet aux futures fonctions du jeu
    # de consulter la météo choisie.

    if not config.chemin_etat("meteo_path").exists():
        return None

    meteo = config.chemin_etat("meteo_path").read_text(
        encoding="utf-8"
    ).strip()

    if meteo == "":
        return None

    return meteo
