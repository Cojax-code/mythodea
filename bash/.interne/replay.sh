#!/bin/bash
# Lecture non privilégiée : les permissions du joueur s'appliquent normalement.
# Fonction isolée en sous-shell pour préserver les traps et hooks du shell SSH.
replay() (
    if ! declare -F _mythodea_afficher >/dev/null; then
        source "$(dirname -- "${BASH_SOURCE[0]}")/terminal.sh"
    fi
    local immediat=0
    if [[ ${1-} == --immediat ]]; then immediat=1; shift; fi
    if [[ $# != 1 || ! -f $1 || ! -r $1 ]]; then
        printf 'Usage : replay [--immediat] chemin/rapport.txt (fichier lisible requis)\n' >&2
        exit 1
    fi
    local delai=${MYTHODEA_DELAI:-0.5} ligne
    (( immediat )) && delai=0
    local exploration=0 camp=''
    [[ ${1##*/} == rapport_exploration.txt ]] && exploration=1
    if [[ ! $delai =~ ^[0-9]+([.][0-9]+)?$ ]]; then
        printf 'MYTHODEA_DELAI doit être un nombre positif ou nul, par exemple 0.5.\n' >&2
        exit 2
    fi
    trap 'exit 130' INT
    while IFS= read -r ligne || [[ -n $ligne ]]; do
        if (( exploration )); then
            case $ligne in j1|j2) camp=32 ;; BOT) camp=31 ;; esac
            _mythodea_exploration "$ligne" "$camp" || exit
        else
            _mythodea_afficher "$ligne" || exit
        fi
        [[ $delai == 0 ]] || sleep "$delai" || exit
    done < "$1"
)

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    replay "$@"
fi
