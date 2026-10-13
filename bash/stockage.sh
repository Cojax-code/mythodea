#!/bin/bash
# Fonctions partagées des scripts administratifs. Aucun nettoyage au chargement.

verifier_stockage() {
    local racine
    racine="$(python3 -B - "$PROJECT_DIR/python" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import config
config.verifier_partition_plateau()
print(config.game_path)
PY
    )" || return 1
    # Seconde barrière avant toute expansion utilisée par un nettoyage.
    case "$racine" in
        /game) GAME_PATH="$racine" ;;
        /|/home|/home/j1|/home/j2|*)
            echo "Erreur : cible de nettoyage interdite : $racine (/game attendu)." >&2
            return 1 ;;
    esac
}

verifier_sous_montages() {
    local montages montage
    montages="$(findmnt -rn -o TARGET)" || return 1
    while IFS= read -r montage; do
        case "$montage" in
            "$GAME_PATH"/*|/home/j1/general*|/home/j2/general*)
                echo "Erreur : sous-montage à examiner avant nettoyage : $montage" >&2
                return 1 ;;
        esac
    done <<< "$montages"
}

vider_plateau() {
    verifier_stockage || return 1
    verifier_sous_montages || return 1
    # Pas de glob : inclut .systeme et tous les autres fichiers cachés.
    # mindepth 1 conserve le point de montage lui-même ; aucun lien n'est suivi.
    if [[ ${1:-} == conserver_verrou_survie ]]; then
        # Seul le verrou créé par le reset reste présent jusqu'à sa sortie.
        find "$GAME_PATH/.systeme" -mindepth 1 -maxdepth 1 ! -name verrou_cycle_survie -exec rm -rf --one-file-system -- {} +
        find "$GAME_PATH" -mindepth 1 -maxdepth 1 ! -name .systeme -exec rm -rf --one-file-system -- {} +
    else
        find "$GAME_PATH" -mindepth 1 -maxdepth 1 -exec rm -rf --one-file-system -- {} +
    fi
}
