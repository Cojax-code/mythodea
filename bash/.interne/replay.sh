#!/bin/bash
# Lecture non privilégiée : les permissions du joueur s'appliquent normalement.
# Fonction isolée en sous-shell pour préserver les traps et hooks du shell SSH.
replay() (
    if ! declare -F _mythodea_afficher >/dev/null; then
        source "$(dirname -- "${BASH_SOURCE[0]}")/terminal.sh"
    fi
    if [[ $# != 1 || ! -f $1 || ! -r $1 ]]; then
        printf 'Usage : replay chemin/rapport.txt (fichier lisible requis)\n' >&2
        exit 1
    fi
    local delai=${MYTHODEA_DELAI:-0.5} ligne
    if [[ ! $delai =~ ^[0-9]+([.][0-9]+)?$ ]]; then
        printf 'MYTHODEA_DELAI doit être un nombre positif ou nul, par exemple 0.5.\n' >&2
        exit 2
    fi
    trap 'exit 130' INT
    while IFS= read -r ligne || [[ -n $ligne ]]; do
        _mythodea_afficher "$ligne" || exit
        sleep "$delai" || exit
    done < "$1"
)

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    replay "$@"
fi
