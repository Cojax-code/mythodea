#!/bin/bash

echo "Nettoyage de Mythodea..."

# Nettoyer les rapports
sudo rm -f /home/game/rapport/rapport_bataille.txt
sudo rm -f /home/game/rapport/rapport_court.txt
sudo rm -f /home/game/etat.txt

# Nettoyer les unités dans tous les blocs
for territoire in base1 terrain1 terrain2 terrain3 base2
do
    for joueur in j1 j2
    do
        for bloc in avant droite gauche arriere
        do
            sudo rm -rf /home/game/$territoire/$joueur/$bloc/*
        done
    done
done

# Nettoyer les tentatives de victoire
sudo truncate -s 0 /home/game/base1/tentative_j2.txt
sudo truncate -s 0 /home/game/base2/tentative_j1.txt

# Nettoyer les unités connues
sudo rm -f /home/game/systeme/unites_connues.txt

echo "Nettoyage terminé."