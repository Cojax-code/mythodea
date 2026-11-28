#!/usr/bin/env bash
# Installation/mise à jour Survie sans reset ni effacement des homes.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Erreur : lance ce script avec sudo."
    echo "Exemple : sudo bash bash/instal.sh"
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/.interne/stockage.sh"
verifier_stockage
verifier_sous_montages
for fichier in "$GAME_PATH/.systeme/verrou_cycle_survie" "$GAME_PATH/.systeme/gel_survie.json"; do
    [[ ! -e $fichier && ! -L $fichier ]] || { echo "Diagnostic requis : $fichier" >&2; exit 1; }
done

for joueur in j1 j2; do
    if id "$joueur" &>/dev/null; then
        echo "L'utilisateur $joueur existe déjà."
    else
        echo "Création de l'utilisateur $joueur..."
        useradd --create-home --shell /bin/bash "$joueur"
    fi

    getent group "$joueur" >/dev/null || groupadd "$joueur"
done

getent group mythodea_allies >/dev/null || groupadd mythodea_allies
for joueur in j1 j2; do
    usermod -aG mythodea_allies "$joueur"
done
python3 "$PROJECT_DIR/python/crypte_installer.py"

echo 'Installation Survie terminée, sans reset. Reconnecter les joueurs en SSH.'
echo 'Lancement : sudo bash bash/start.sh'
