#!/bin/bash

echo "Nettoyage de Mythodea..."

# Liste des territoires
territoires="base1 terrain1 terrain2 terrain3 base2"
joueurs="j1 j2"
blocs="avant droite gauche arriere"

# 1. Réouvrir les dossiers pour permettre le nettoyage
echo "Restauration temporaire des permissions..."

for territoire in $territoires
do
    for joueur in $joueurs
    do
        sudo chmod 700 /home/game/$territoire/$joueur 2>/dev/null

        for bloc in $blocs
        do
            sudo chmod 700 /home/game/$territoire/$joueur/$bloc 2>/dev/null
        done
    done
done

sudo chmod 700 /home/j1 2>/dev/null
sudo chmod 700 /home/j2 2>/dev/null

# 2. Nettoyer les rapports
echo "Nettoyage des rapports..."

sudo rm -f /home/game/rapport/rapport_bataille.txt
sudo rm -f /home/game/rapport/rapport_court.txt
sudo rm -f /home/game/etat.txt

# 3. Nettoyer les unités dans tous les blocs
echo "Nettoyage des unités..."

for territoire in $territoires
do
    for joueur in $joueurs
    do
        for bloc in $blocs
        do
            sudo sh -c "rm -rf /home/game/$territoire/$joueur/$bloc/*"
        done
    done
done

# 4. Nettoyer les tentatives de victoire
echo "Nettoyage des tentatives..."

sudo truncate -s 0 /home/game/base1/tentative_j2.txt 2>/dev/null
sudo truncate -s 0 /home/game/base2/tentative_j1.txt 2>/dev/null

# 5. Nettoyer les unités connues
echo "Nettoyage du système..."

sudo rm -f /home/game/systeme/unites_connues.txt

# 6. Restaurer propriétaires et permissions normales
echo "Restauration des permissions finales..."

for territoire in $territoires
do
    for joueur in $joueurs
    do
        sudo chown $joueur:$joueur /home/game/$territoire/$joueur
        sudo chmod 700 /home/game/$territoire/$joueur

        for bloc in $blocs
        do
            sudo chown $joueur:$joueur /home/game/$territoire/$joueur/$bloc
            sudo chmod 700 /home/game/$territoire/$joueur/$bloc
        done
    done
done

# 7. Restaurer les home des joueurs
sudo chown j1:j1 /home/j1
sudo chmod 700 /home/j1

sudo chown j2:j2 /home/j2
sudo chmod 700 /home/j2

# 8. Protéger les dossiers système
sudo chown -R root:root /home/game/rapport 2>/dev/null
sudo chmod 755 /home/game/rapport 2>/dev/null

sudo chown -R root:root /home/game/systeme 2>/dev/null
sudo chmod 700 /home/game/systeme 2>/dev/null

echo "Nettoyage terminé."
echo "Permissions restaurées."