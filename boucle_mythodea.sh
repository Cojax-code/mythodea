#!/bin/bash

tour=1
etat="/home/game/etat.txt"
rapport="/home/game/rapport/rapport_court.txt"

ouvrir_action() {
    sudo chmod 700 /home/j1 /home/j2

    sudo chmod 700 /home/game/base1/j1 /home/game/base1/j2
    sudo chmod 700 /home/game/terrain1/j1 /home/game/terrain1/j2
    sudo chmod 700 /home/game/base2/j1 /home/game/base2/j2

    sudo chmod 700 /home/game/base1/j1/avant /home/game/base1/j1/droite /home/game/base1/j1/gauche /home/game/base1/j1/arriere
    sudo chmod 700 /home/game/terrain1/j1/avant /home/game/terrain1/j1/droite /home/game/terrain1/j1/gauche /home/game/terrain1/j1/arriere
    sudo chmod 700 /home/game/base2/j1/avant /home/game/base2/j1/droite /home/game/base2/j1/gauche /home/game/base2/j1/arriere

    sudo chmod 700 /home/game/base1/j2/avant /home/game/base1/j2/droite /home/game/base1/j2/gauche /home/game/base1/j2/arriere
    sudo chmod 700 /home/game/terrain1/j2/avant /home/game/terrain1/j2/droite /home/game/terrain1/j2/gauche /home/game/terrain1/j2/arriere
    sudo chmod 700 /home/game/base2/j2/avant /home/game/base2/j2/droite /home/game/base2/j2/gauche /home/game/base2/j2/arriere
}

fermer_action() {
    sudo chmod 500 /home/j1 /home/j2

    sudo chmod 500 /home/game/base1/j1 /home/game/base1/j2
    sudo chmod 500 /home/game/terrain1/j1 /home/game/terrain1/j2
    sudo chmod 500 /home/game/base2/j1 /home/game/base2/j2

    sudo chmod 500 /home/game/base1/j1/avant /home/game/base1/j1/droite /home/game/base1/j1/gauche /home/game/base1/j1/arriere
    sudo chmod 500 /home/game/terrain1/j1/avant /home/game/terrain1/j1/droite /home/game/terrain1/j1/gauche /home/game/terrain1/j1/arriere
    sudo chmod 500 /home/game/base2/j1/avant /home/game/base2/j1/droite /home/game/base2/j1/gauche /home/game/base2/j1/arriere

    sudo chmod 500 /home/game/base1/j2/avant /home/game/base1/j2/droite /home/game/base1/j2/gauche /home/game/base1/j2/arriere
    sudo chmod 500 /home/game/terrain1/j2/avant /home/game/terrain1/j2/droite /home/game/terrain1/j2/gauche /home/game/terrain1/j2/arriere
    sudo chmod 500 /home/game/base2/j2/avant /home/game/base2/j2/droite /home/game/base2/j2/gauche /home/game/base2/j2/arriere
}

while true
do
    ouvrir_action

    echo "===== TOUR $tour =====" | sudo tee "$etat"
    sleep 2

    echo "===== ACTION : 2 minutes 10 =====" | sudo tee "$etat"

    for i in 130 110 90 70 50 30 10
    do
        echo "TOUR $tour - ACTION : encore $i secondes" | sudo tee "$etat"
        sleep 20
    done

    fermer_action

    echo "===== RESOLUTION DES COMBATS =====" | sudo tee "$etat"
    sudo python3 /home/cojax/mythodea.py

    if [ -f "$rapport" ]; then
        sudo cat "$rapport" | sudo tee "$etat"
    fi

    echo "===== PAUSE : 60 secondes =====" | sudo tee -a "$etat"

    for i in 60 50 40 30 20 10
    do
        echo "PAUSE : encore $i secondes" | sudo tee -a "$etat"
        sleep 10
    done

    tour=$((tour + 1))
done