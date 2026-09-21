#!/usr/bin/env bash

set -e

if [[ $EUID -ne 0 ]]; then
    echo "Erreur : lance ce script avec sudo."
    echo "Exemple : sudo ./install_mythodea.sh"
    exit 1
fi

for joueur in j1 j2; do
    if id "$joueur" &>/dev/null; then
        echo "L'utilisateur $joueur existe déjà."
    else
        echo "Création de l'utilisateur $joueur..."
        useradd --create-home --shell /bin/bash "$joueur"
    fi

    chown "$joueur:$joueur" "/home/$joueur"
    chmod 700 "/home/$joueur"
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/nettoyage.sh"

echo "Installation de Mythodea V1.5 terminée."