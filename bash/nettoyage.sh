#!/bin/bash

set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Erreur : utiliser sudo bash bash/nettoyage.sh.' >&2; exit 1; }
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/stockage.sh"
verifier_stockage
verifier_sous_montages

echo "=== Nettoyage Mythodea V1.5 ==="

# Vider la partition validée, fichiers cachés inclus, sans retirer son montage.
vider_plateau

# Recréer les dossiers principaux.
sudo mkdir -p "$GAME_PATH/base1"
sudo mkdir -p "$GAME_PATH/terrain1"
sudo mkdir -p "$GAME_PATH/terrain2"
sudo mkdir -p "$GAME_PATH/terrain3"
sudo mkdir -p "$GAME_PATH/base2"
sudo mkdir -p "$GAME_PATH/rapport"
sudo mkdir -p "$GAME_PATH/.systeme"

# Recréer les dossiers joueurs + emplacements.
for territoire in base1 terrain1 terrain2 terrain3 base2
do
    for joueur in j1 j2
    do
        sudo mkdir -p "$GAME_PATH/$territoire/$joueur/1"
        sudo mkdir -p "$GAME_PATH/$territoire/$joueur/2"
        sudo mkdir -p "$GAME_PATH/$territoire/$joueur/3"
        sudo mkdir -p "$GAME_PATH/$territoire/$joueur/4"

        sudo chown -R $joueur:$joueur "$GAME_PATH/$territoire/$joueur"
        sudo chmod -R 700 "$GAME_PATH/$territoire/$joueur"
    done
done

# Nettoyage complet des homes des joueurs
echo "Nettoyage des homes j1 et j2..."

sudo find /home/j1 -mindepth 1 -maxdepth 1 -exec rm -rf {} +
sudo find /home/j2 -mindepth 1 -maxdepth 1 -exec rm -rf {} +

sudo chown j1:j1 /home/j1
sudo chmod 700 /home/j1

sudo chown j2:j2 /home/j2
sudo chmod 700 /home/j2

# Nettoyer les anciens généraux dans les homes.
sudo rm -rf /home/j1/general1 /home/j1/general2 /home/j1/general3 /home/j1/general4 /home/j1/general5
sudo rm -rf /home/j2/general1 /home/j2/general2 /home/j2/general3 /home/j2/general4 /home/j2/general5

# Recréer les fichiers de victoire.
sudo touch "$GAME_PATH/base1/objectif.txt"
sudo touch "$GAME_PATH/base2/objectif.txt"
sudo touch "$GAME_PATH/base1/tentative_j2.txt"
sudo touch "$GAME_PATH/base2/tentative_j1.txt"

# Exemple d'objectifs.
echo "lezard" | sudo tee "$GAME_PATH/base1/objectif.txt" > /dev/null
echo "dragon" | sudo tee "$GAME_PATH/base2/objectif.txt" > /dev/null

# Permissions objectifs.
# j2 doit pouvoir lire l'objectif de base1.
sudo chown root:j2 "$GAME_PATH/base1/objectif.txt"
sudo chmod 640 "$GAME_PATH/base1/objectif.txt"

# j1 doit pouvoir lire l'objectif de base2.
sudo chown root:j1 "$GAME_PATH/base2/objectif.txt"
sudo chmod 640 "$GAME_PATH/base2/objectif.txt"

# Permissions tentatives.
sudo chown j2:j2 "$GAME_PATH/base1/tentative_j2.txt"
sudo chmod 600 "$GAME_PATH/base1/tentative_j2.txt"

sudo chown j1:j1 "$GAME_PATH/base2/tentative_j1.txt"
sudo chmod 600 "$GAME_PATH/base2/tentative_j1.txt"

# Permissions rapport et système.
sudo chown -R root:root "$GAME_PATH/rapport"
sudo chmod -R 755 "$GAME_PATH/rapport"

sudo chown -R root:root "$GAME_PATH/.systeme"
sudo chmod -R 755 "$GAME_PATH/.systeme"

echo "Nettoyage V1.5 terminé."
echo "Lance ensuite : ./start_v15.sh"
