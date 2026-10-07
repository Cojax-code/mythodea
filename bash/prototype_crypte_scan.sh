# Prototype d'observation uniquement : aucune API de jeu, aucun generalN.
# A sourcer depuis un rcfile administrateur, dans un Bash interactif isolé.
# Le lanceur de test ouvre le FD 9 vers son journal, hors de l'atelier jetable.
# Ce journal et ces variables NE constituent PAS un état moteur de confiance.

_crypte_active=0
_crypte_pending=0
_crypte_sequence=0

_crypte_event() {
    # Enregistre huit champs séparés par NUL, sans eval ni échappement ambigu.
    builtin printf '%s\0' "$1" "${2-}" "${3-}" "${4-}" "${5-}" \
        "${6-}" "${7-}" "$BASHPID" >&9
}

_crypte_history() {
    _crypte_line=''
    _crypte_hid=''
    _crypte_history_ok=0
    [[ -o history && -z $HISTCONTROL && -z $HISTIGNORE && $HISTSIZE != 0 ]] || return 0
    local entry
    entry=$(HISTTIMEFORMAT= builtin history 1)
    if [[ $entry =~ ^[[:blank:]]*([0-9]+)[[:blank:]]+(.*)$ ]]; then
        _crypte_hid=${BASH_REMATCH[1]}
        _crypte_line=${BASH_REMATCH[2]}
        _crypte_history_ok=1
    fi
}

_crypte_before() {
    local command=$1 previous=$2 kind name
    # Les hooks ne doivent pas observer leur propre instrumentation.
    [[ $command == '_crypte_prompt "$?"' ]] && return 0
    (( _crypte_active )) || return 0
    _crypte_history
    # DEBUG peut aussi précéder un trap de signal avec un BASH_COMMAND périmé.
    # Une ligne complète n'est enregistrée qu'une fois (y compris les listes ;).
    if (( _crypte_history_ok )) && [[ $_crypte_hid == $_crypte_last_hid ]]; then
        return 0
    fi
    _crypte_last_hid=$_crypte_hid
    name=${command%% *}
    kind=$(builtin type -t -- "$name")
    _crypte_event before "$_crypte_line" "$command" "$previous" \
        "$(builtin pwd -P)" "$_crypte_hid/$_crypte_history_ok" "$kind"
    _crypte_pending=1
}

_crypte_prompt() {
    local result=$1
    if (( _crypte_active && ! _crypte_pending )); then
        # Une erreur de syntaxe n'exécute aucune commande et ne déclenche pas
        # DEBUG. Ne pas perdre sa ligne au prochain retour à l'invite.
        _crypte_history
        if (( _crypte_history_ok )) && [[ $_crypte_hid != $_crypte_last_hid ]]; then
            _crypte_event unobserved "$_crypte_line" '' "$result" \
                "$(builtin pwd -P)" "$_crypte_hid/$_crypte_history_ok"
            _crypte_last_hid=$_crypte_hid
        fi
    fi
    if (( _crypte_active && _crypte_pending )); then
        _crypte_event after '' '' "$result" "$(builtin pwd -P)"
    elif (( _crypte_active && result == 130 )); then
        _crypte_event interrupt '' '' "$result" "$(builtin pwd -P)"
    fi
    _crypte_pending=0
}

_crypte_interrupt() {
    if (( _crypte_active )); then
        _crypte_event interrupt '' '' 130 "$(builtin pwd -P)"
        _crypte_pending=0
    fi
}

_crypte_exit() {
    if (( _crypte_active )); then
        _crypte_event close '' '' "$1" "$(builtin pwd -P)"
    fi
}

crypte_commence() {
    if (( _crypte_active )); then
        _crypte_event refused 'tentative deja ouverte'
        return 1
    fi
    _crypte_old_control=${HISTCONTROL-}
    _crypte_old_ignore=${HISTIGNORE-}
    _crypte_old_size=${HISTSIZE-500}
    _crypte_old_history=0
    _crypte_old_histexpand=0
    [[ -o history ]] && _crypte_old_history=1
    [[ -o histexpand ]] && _crypte_old_histexpand=1
    HISTCONTROL= HISTIGNORE=
    # Ne pas tronquer un historique personnel plus grand ou illimité.
    [[ ${HISTSIZE-0} == 0 ]] && HISTSIZE=1000
    set -o history
    set +o histexpand
    _crypte_active=1
    _crypte_pending=0
    _crypte_history
    _crypte_last_hid=$_crypte_hid
    ((_crypte_sequence+=1))
    _crypte_event start '' '' '' "$(builtin pwd -P)" "$_crypte_sequence" "$UID"
}

crypte_fin() {
    if (( ! _crypte_active )); then
        _crypte_event refused 'aucune tentative'
        return 1
    fi
    _crypte_event end '' '' '' "$(builtin pwd -P)"
    _crypte_active=0
    _crypte_pending=0
    _crypte_restaurer_historique
    return 0
}

_crypte_restaurer_historique() {
    HISTCONTROL=$_crypte_old_control
    HISTIGNORE=$_crypte_old_ignore
    HISTSIZE=$_crypte_old_size
    (( _crypte_old_history )) || set +o history
    (( _crypte_old_histexpand )) && set -o histexpand
    return 0
}

# Le prototype exige un rcfile dédié : ne remplace pas les hooks d'une vraie partie.
PROMPT_COMMAND='_crypte_prompt "$?"'
trap '_crypte_before "$BASH_COMMAND" "$?"' DEBUG
trap '_crypte_interrupt' INT
trap '_crypte_exit "$?"' EXIT
trap 'exit 129' HUP
