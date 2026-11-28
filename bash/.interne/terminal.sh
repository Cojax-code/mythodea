# Fonctions d'affichage non privilégiées ; aucun code ANSI dans les fichiers.
_mythodea_couleurs() {
    [[ -t 1 && ${MYTHODEA_COULEURS-1} != 0 && ${TERM-dumb} != dumb && -n ${TERM-} ]]
}

_mythodea_nettoyer() {
    local LC_ALL=C.UTF-8
    local texte=$1 caractere
    # Les données joueurs ne doivent jamais devenir des commandes de terminal.
    # Conserver tabulations et sauts de ligne pour les tableaux.
    while [[ $texte =~ [$'\001-\010\013-\037\177'] ]]; do
        caractere=${BASH_REMATCH[0]}
        texte=${texte//"$caractere"/}
    done
    while [[ $texte =~ [$'\302\200-\302\237'] ]]; do
        caractere=${BASH_REMATCH[0]}
        texte=${texte//"$caractere"/}
    done
    REPLY=$texte
}

_mythodea_afficher() {
    local REPLY texte couleur=''
    _mythodea_nettoyer "$1"
    texte=$REPLY
    if _mythodea_couleurs; then
        case ${texte,,} in
            *erreur*|*refus*|*défaite*|*perte*) couleur=31 ;;
            *fatigue*|*bless*|*gel\ temporaire*|*avertissement*) couleur=33 ;;
            *réuss*|*succès*|*victoire*|*progression*|*récompense*) couleur=32 ;;
            phase*|tour*|===*|*phase\ de*|*rapports\ disponibles*) couleur=36 ;;
        esac
    fi
    if [[ -n $couleur ]]; then
        builtin printf '\033[%sm%s\033[0m\n' "$couleur" "$texte"
    else
        builtin printf '%s\n' "$texte"
    fi
}

_mythodea_exploration() {
    local REPLY texte couleur=''
    _mythodea_nettoyer "$1"
    texte=$REPLY
    if _mythodea_couleurs; then
        case $texte in
            RAPPORT*|VILLAGE|EST_*|REPLI|===*) couleur=36 ;;
            *contesté*|*avertissement*|*sanction*) couleur=33 ;;
            'Contrôle : bot'|BOT) couleur=31 ;;
            'Contrôle : allié'|j1|j2) couleur=32 ;;
            *' — '*unité*) couleur=$2 ;;
        esac
    fi
    if [[ -n $couleur ]]; then
        builtin printf '\033[%sm%s\033[0m\n' "$couleur" "$texte"
    else
        builtin printf '%s\n' "$texte"
    fi
}

_mythodea_prompt() {
    local resultat=$? logique=$PWD
    # PWD garde le chemin logique même si Linux a renommé son inode.
    case $logique in
        /game/*|"$HOME"/general*|"$HOME"/amelie_poulin[1-9]*|"$HOME"/har_chez_moi[1-9]*|"$HOME"/pic_nic[1-9]*)
            if [[ ! . -ef $logique ]]; then
                if ! builtin cd -L -- "$logique" 2>/dev/null; then
                    builtin cd -- "$HOME" || return "$resultat"
                    _mythodea_afficher 'Mythodea : ce répertoire a disparu ; retour au home.'
                fi
            fi ;;
    esac
    local REPLY
    _mythodea_nettoyer "$PWD"
    _mythodea_repertoire=${REPLY//$'\n'/\?}
    _mythodea_repertoire=${_mythodea_repertoire//$'\t'/\?}
    if _mythodea_couleurs; then
        PS1='\[\e[36m\]\u@\h\[\e[0m\]:\[\e[33m\]${_mythodea_repertoire}\[\e[0m\]\$ '
    else
        PS1='\u@\h:${_mythodea_repertoire}\$ '
    fi
    # Préférence par terminal, sans interprétation par le moteur.
    local tty fichier valeur=0
    _mythodea_couleurs && valeur=1
    tty=$(tty 2>/dev/null) || return "$resultat"
    if [[ $tty =~ ^/dev/pts/([0-9]+)$ && -d /run/user/$UID ]]; then
        fichier=/run/user/$UID/mythodea-pts-${BASH_REMATCH[1]}
        [[ -L $fichier ]] || (umask 077; printf '%s' "$valeur" > "$fichier")
    fi
    return "$resultat"
}

_mythodea_installer_prompt() {
    # Fonctionne avec PROMPT_COMMAND scalaire ou tableau. Le scanner Crypte
    # reste premier et clôt son instrumentation en dernier.
    local commande
    local -a commandes=()
    for commande in "${PROMPT_COMMAND[@]}"; do
        case $commande in
            _crypte_sortie_prompt|_mythodea_prompt|'_crypte_prompt "$?" "${PIPESTATUS[*]}"') ;;
            *) commandes+=("$commande") ;;
        esac
    done
    PROMPT_COMMAND=("${commandes[@]}" '_mythodea_prompt')
    if declare -F _crypte_sortie_prompt >/dev/null; then
        PROMPT_COMMAND=('_crypte_prompt "$?" "${PIPESTATUS[*]}"' "${PROMPT_COMMAND[@]}" '_crypte_sortie_prompt')
    fi
}
