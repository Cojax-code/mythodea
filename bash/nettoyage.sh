#!/bin/bash

echo "=== Nettoyage Mythodea V1.5 ==="

# Supprimer l'ancien plateau.
sudo rm -rf /home/game

# Recréer les dossiers principaux.
sudo mkdir -p /home/game/base1
sudo mkdir -p /home/game/terrain1
sudo mkdir -p /home/game/terrain2
sudo mkdir -p /home/game/terrain3
sudo mkdir -p /home/game/base2
sudo mkdir -p /home/game/rapport
sudo mkdir -p /home/game/systeme

# Recréer les dossiers joueurs + emplacements.
for territoire in base1 terrain1 terrain2 terrain3 base2
do
    for joueur in j1 j2
    do
        sudo mkdir -p /home/game/$territoire/$joueur/1
        sudo mkdir -p /home/game/$territoire/$joueur/2
        sudo mkdir -p /home/game/$territoire/$joueur/3
        sudo mkdir -p /home/game/$territoire/$joueur/4

        sudo chown -R $joueur:$joueur /home/game/$territoire/$joueur
        sudo chmod -R 700 /home/game/$territoire/$joueur
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
sudo touch /home/game/base1/objectif.txt
sudo touch /home/game/base2/objectif.txt
sudo touch /home/game/base1/tentative_j2.txt
sudo touch /home/game/base2/tentative_j1.txt

# Exemple d'objectifs.
echo "lezard" | sudo tee /home/game/base1/objectif.txt > /dev/null
echo "dragon" | sudo tee /home/game/base2/objectif.txt > /dev/null

# Permissions objectifs.
# j2 doit pouvoir lire l'objectif de base1.
sudo chown root:j2 /home/game/base1/objectif.txt
sudo chmod 640 /home/game/base1/objectif.txt

# j1 doit pouvoir lire l'objectif de base2.
sudo chown root:j1 /home/game/base2/objectif.txt
sudo chmod 640 /home/game/base2/objectif.txt

# Permissions tentatives.
sudo chown j2:j2 /home/game/base1/tentative_j2.txt
sudo chmod 600 /home/game/base1/tentative_j2.txt

sudo chown j1:j1 /home/game/base2/tentative_j1.txt
sudo chmod 600 /home/game/base2/tentative_j1.txt

# Permissions rapport et système.
sudo chown -R root:root /home/game/rapport
sudo chmod -R 755 /home/game/rapport

sudo chown -R root:root /home/game/systeme
sudo chmod -R 755 /home/game/systeme

echo "Nettoyage V1.5 terminé."
echo "Lance ensuite : ./start_v15.sh"