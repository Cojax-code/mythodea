"""Configuration, carte et chemins du jeu."""
from pathlib import Path

game_path = Path("/home/game")

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
    game_path / "systeme" / "positions_generaux.txt"
)

fatigue_generaux_path = (
    game_path / "systeme" / "fatigue_generaux.txt"
)

repli_path = game_path / "repli"


ordre_blocs = ["avant", "droite", "gauche", "arriere"]
joueurs = ["j1", "j2"]

emplacements = ["1", "2", "3","4"]
max_unites_par_general = 20
max_generaux_par_joueur = 5

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
    "1-1": {
        "type": 1,
        "numero": 1,
        "nom": "retraite_apres_premiere_manche",
        "categorie": "armee",
    },

    "1-2": {
        "type": 1,
        "numero": 2,
        "nom": "attaque_frontale",
        "categorie": "armee",
    },

    "2-1": {
        "type": 2,
        "numero": 1,
        "nom": "attaque_chirurgicale",
        "categorie": "formation",
    },

    "2-2": {
        "type": 2,
        "numero": 2,
        "nom": "pluie_de_fleches",
        "categorie": "formation",
    },

    "3-1": {
        "type": 3,
        "numero": 1,
        "nom": "fuir_avant_la_mort",
        "categorie": "intrinseque",
    },
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
    / "systeme"
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

controle_territoires_path = game_path / "systeme" / "controle_territoires.txt"


modes_disponibles = ("classique", "survie")


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
        "permissions_generaux": {"dossiers": 0o700, "fichiers": 0o600},
        "duree_phase_action_secondes": duree_action,
    }
