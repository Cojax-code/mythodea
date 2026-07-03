#!/bin/bash

echo "Nettoyage de Mythodea..."

# Réouvrir temporairement les dossiers du jeu
for territoire in base1 terrain1 terrain2 terrain3 base2
do
    for joueur in j1 j2
    do
        sudo chmod 700 /home/game/$territoire/$joueur 2>/dev/null

        for bloc in avant droite gauche arriere
        do
            sudo chmod 700 /home/game/$territoire/$joueur/$bloc 2>/dev/null
        done
    done
done

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
            sudo sh -c "rm -rf /home/game/$territoire/$joueur/$bloc/*"
        done
    done
done

# Nettoyer les tentatives de victoire
sudo truncate -s 0 /home/game/base1/tentative_j2.txt 2>/dev/null
sudo truncate -s 0 /home/game/base2/tentative_j1.txt 2>/dev/null

# Nettoyer les unités connues
sudo rm -f /home/game/systeme/unites_connues.txt

# Remettre les bonnes permissions pour jouer
for territoire in base1 terrain1 terrain2 terrain3 base2
do
    for joueur in j1 j2
    do
        sudo chown $joueur:$joueur /home/game/$territoire/$joueur
        sudo chmod 700 /home/game/$territoire/$joueur

        for bloc in avant droite gauche arriere
        do
            sudo chown $joueur:$joueur /home/game/$territoire/$joueur/$bloc
            sudo chmod 700 /home/game/$territoire/$joueur/$bloc
        done
    done
done

echo "Nettoyage terminé."