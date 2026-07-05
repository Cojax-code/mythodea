#!/bin/bash

echo "=== Lancement Mythodea V1.5 ==="

# On lance le script Python principal.
sudo python3 /home/cojax/mythodea.py

echo
echo "=== Rapport court ==="

if [ -f /home/game/rapport/rapport_court.txt ]; then
    cat /home/game/rapport/rapport_court.txt
else
    echo "Aucun rapport court trouvé."
fi