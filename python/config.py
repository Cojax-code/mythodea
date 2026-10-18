"""Configuration, carte et chemins du jeu."""
from pathlib import Path
from contextlib import contextmanager
from contextvars import ContextVar
import catalogues


_generation = ContextVar("generation_metier", default=None)
ETATS_METIER = (
    "compteur_general_j1.txt", "compteur_general_j2.txt", "compteur_general_bot.txt",
    "positions_generaux.txt", "fatigue_generaux.txt", "controle_territoires.txt",
    "attente_repli.txt", "meteo.txt",
    "crypte.json", "compteur_creation_normale_j1.txt", "compteur_creation_normale_j2.txt",
    "unites_actions.json",
    "defis.json",
    "progression.json",
    "soldats.json",
    "formation.json",
)


@contextmanager
def racines_generation(plateau, homes):
    """Redirige explicitement les accès métier, sans modifier les globaux classiques."""
    jeton = _generation.set((plateau, homes))
    try:
        yield
    finally:
        _generation.reset(jeton)


def racine_metier():
    courant = _generation.get()
    return courant[0] if courant else game_path


def dans_generation_privee():
    return _generation.get() is not None


def home_generation(joueur):
    courant = _generation.get()
    return courant[1][joueur] if courant else None


def chemin_etat(nom):
    courant = _generation.get()
    return courant[0] / ".systeme" / globals()[nom].name if courant else globals()[nom]

GAME_PATH_OFFICIEL = Path("/game")
game_path = GAME_PATH_OFFICIEL
# Les exemples joueurs visent le plateau publié, jamais une génération privée.
game_public_path = GAME_PATH_OFFICIEL


def verifier_partition_plateau():
    """Contrôle Linux en lecture seule, réservé aux points d'entrée réels.

    Les API métier gardent leurs configurations temporaires injectables en test.
    Aucune création, migration, opération de montage ou de formatage ici.
    """
    import json
    import subprocess

    if game_path != GAME_PATH_OFFICIEL:
        raise RuntimeError(f'Racine de production interdite : {game_path} ; /game attendu.')
    if game_path.is_symlink() or not game_path.is_dir():
        raise RuntimeError('/game doit exister, sans lien symbolique, avant le lancement.')
    try:
        resultat = subprocess.run(
            ['findmnt', '--json', '--mountpoint', game_path.as_posix(),
             '--output', 'TARGET,FSROOT,OPTIONS'],
            check=True, capture_output=True, text=True,
        )
        montages = json.loads(resultat.stdout)['filesystems']
        if len(montages) != 1:
            raise ValueError('montage ambigu')
        montage = montages[0]
        valide = (montage['target'] == game_path.as_posix()
                  and montage['fsroot'] == '/'
                  and 'rw' in montage['options'].split(','))
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError, TypeError) as erreur:
        raise RuntimeError('/game doit être un point de montage dédié ; vérifier findmnt --mountpoint /game.') from erreur
    if (not valide or game_path.stat().st_dev in
            {Path('/').stat().st_dev, Path('/home').stat().st_dev}):
        raise RuntimeError('/game exige une partition entière, accessible en écriture, distincte de / et /home.')

territoires = [
    game_path / "base1",
    game_path / "terrain1",
    game_path / "terrain2",
    game_path / "terrain3",
    game_path / "base2",
]

carte_territoires = {
    "base1": ["terrain1"],
    "terrain1": ["base1", "terrain2"],
    "terrain2": ["terrain1", "terrain3"],
    "terrain3": ["terrain2", "base2"],
    "base2": ["terrain3"],
}

bases_joueurs = {
    "j1": "base1",
    "j2": "base2",
}

positions_generaux_path = (
    game_path / ".systeme" / "positions_generaux.txt"
)

fatigue_generaux_path = (
    game_path / ".systeme" / "fatigue_generaux.txt"
)

repli_path = game_path / "repli"


ordre_blocs = ["avant", "droite", "gauche", "arriere"]
joueurs = ["j1", "j2"]

emplacements = ["1", "2", "3","4"]
max_unites_par_general = 20
max_generaux_par_joueur = 5

# Représentations reconnues par le moteur ; ce catalogue n'accorde aucun droit
# d'entraînement. La cavalerie lourde est réservée aux attributions privées.
unites_equipements = {
    unite['nom']: (unite['prefixe'], unite['recette'])
    for unite in catalogues.UNITES.values()
}

orientations = ["stratege", "combattant"]
orientation_rare = "hybride"

# ==================================================
# ORDRES DES GÉNÉRAUX
# ==================================================
#
# Format dans ordre.txt :
#
# type-numero
#
# ou, si l'ordre demande une précision :
#
# type-numero-specification
#
# Exemples :
#
# 1-1
# 2-2
# 2-2-1
#
# Un ordre inconnu, mal écrit ou non applicable
# est simplement ignoré.

legende_ordres = {
    ordre['jeton']: {
        'type': int(ordre['jeton'].split('-')[0]),
        'numero': int(ordre['jeton'].split('-')[1]),
        'nom': ordre['nom'],
        'categorie': {'globale': 'armee', 'duel': 'formation',
                      'individuelle': 'intrinseque'}[ordre['categorie']],
    }
    for ordre in catalogues.ORDRES.values()
}


rapport_dir = game_path / "rapport"

rapport_court_path = (
    rapport_dir
    / "rapport_court.txt"
)

rapport_long_path = (
    rapport_dir
    / "rapport_long.txt"
)

rapports_territoires_dir = (
    rapport_dir
    / "territoires"
)

meteo_path = (
    game_path
    / ".systeme"
    / "meteo.txt"
)

meteos_possibles = [
    "clair",
    "pluie",
    "brouillard",
    "vent",
    "orage",
    "neige",
]

controle_territoires_path = game_path / ".systeme" / "controle_territoires.txt"


modes_disponibles = ("classique", "survie")


def verifier_structure_actuelle(configuration):
    """Refuse les anciens chemins avant toute écriture, même s'ils sont vides."""
    racine = configuration['game_path']
    anciens = [racine / 'systeme']
    if configuration['mode'] == 'survie':
        anciens += [racine / nom for nom in ('clocher', 'communication')]
        anciens += [racine / 'village' / j / nom
                    for j in configuration['joueurs'] for nom in ('poste', 'clocher', 'renforts')]
    for chemin in anciens:
        if chemin.exists() or chemin.is_symlink():
            raise RuntimeError(f'Ancienne structure incompatible : {chemin}. '
                               'Arrêter le moteur et faire archiver la partie par un administrateur ; '
                               'aucune migration automatique ni suppression effectuée.')


def configuration_mode(mode):
    """Décrit un mode sans modifier la configuration globale V1.5 ni le disque.

    Les acteurs sont des identités de jeu, distinctes des comptes Linux et
    des camps militaires. Chaque appel retourne des données indépendantes.
    Le profil Survie prépare le moteur futur ; il n'active pas ses règles.
    """
    if mode not in modes_disponibles:
        raise ValueError(f"Mode inconnu : {mode}")

    acteurs = {
        joueur: {
            "proprietaire_linux": joueur,
            "groupe_linux": joueur,
            "camp": joueur if mode == "classique" else "allies",
        }
        for joueur in joueurs
    }

    if mode == "classique":
        carte = {nom: list(voisins) for nom, voisins in carte_territoires.items()}
        bases = dict(bases_joueurs)
        territoires_mode = list(territoires)
        duree_action = None  # Le lancement classique résout un seul tour.
    else:
        carte = {
            "repli": ["village"],
            "village": ["repli", "est_1"],
            "est_1": ["village", "est_2"],
            "est_2": ["est_1", "est_3"],
            "est_3": ["est_2"],
        }
        bases = {joueur: "village" for joueur in joueurs}
        # Le repli est relié au village mais reste une zone spéciale.
        territoires_mode = [game_path / nom for nom in carte if nom != "repli"]
        acteurs["bot"] = {
            "proprietaire_linux": "root",
            "groupe_linux": "root",
            "camp": "bot",
        }
        duree_action = 120

    return {
        "mode": mode,
        "game_path": game_path,
        "game_public_path": game_public_path,
        "territoires": territoires_mode,
        "carte_territoires": carte,
        "bases_joueurs": bases,
        "repli_path": repli_path,
        "zones_speciales": ["home", "repli"],
        "joueurs": list(joueurs),
        "acteurs": acteurs,
        "emplacements": list(emplacements),
        "positions_renforts_allies": [str(n) for n in range(5, 21)] if mode == "survie" else [],
        "emplacements_partages": mode == "survie",
        "villages": ["village"] if mode == "survie" else [],
        "emplacements_hopital": [str(n) for n in range(1, 21)],
        "emplacements_ecole": [str(n) for n in range(1, 7)],
        "permissions_generaux": {"dossiers": 0o700, "fichiers": 0o600},
        "duree_phase_action_secondes": duree_action,
        "duree_consultation_secondes": 60,
        "duree_gel_secondes": 10,
        "seuil_capture_secondes": 120,
        "groupe_allie": "mythodea_allies",
        # Seuls les camps joueurs inscrits ici peuvent lire les lieux conquis.
        # L'appartenance effective est portée par les groupes Unix des sessions.
        "groupes_camps": ({"allies": "mythodea_allies"} if mode == "survie"
                          else {j: acteurs[j]["groupe_linux"] for j in joueurs}),
    }
