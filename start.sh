#!/bin/bash

echo "=== Lancement Mythodea V1.5 ==="

cd /home/cojax/mythodea_v1.5 || exit 1

sudo python3 mythodea.py

echo
echo "=== Rapport bataille ==="
cat /home/game/rapport/rapport_bataille.txt