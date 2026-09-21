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
