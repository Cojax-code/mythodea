# Prototype d'observation uniquement : aucune API de jeu, aucun generalN.
# A sourcer depuis un rcfile administrateur, dans un Bash interactif isolé.
# Le lanceur de test ouvre le FD 9 vers son journal, hors de l'atelier jetable.
# Ce journal et ces variables NE constituent PAS un état moteur de confiance.

_crypte_active=0
_crypte_pending=0
_crypte_sequence=0
_crypte_ouverture=0

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
    local command=$1 previous=$2 kind name event=before
    # Les hooks ne doivent pas observer leur propre instrumentation.
    [[ $command == '_crypte_prompt "$?" "${PIPESTATUS[*]}"' || ${_crypte_dans_prompt-0} == 1 ]] && return 0
    (( _crypte_active )) || return 0
    _crypte_history
    # DEBUG peut aussi précéder un trap de signal avec un BASH_COMMAND périmé.
    # Une seule étape par ligne ; les autres composants restent observables.
    if (( _crypte_history_ok && ! _crypte_ouverture )) && [[ $_crypte_hid == $_crypte_last_hid ]]; then
        (( _crypte_pending )) || return 0
        event=component
    fi
    _crypte_last_hid=$_crypte_hid
    name=${command%% *}
    kind=$(builtin type -t -- "$name")
    _crypte_event "$event" "$_crypte_line" "$command" "$previous" \
        "$(builtin pwd -P)" "$_crypte_hid/$_crypte_history_ok" "$kind"
    _crypte_pending=1
}

_crypte_prompt() {
    local result=$1 statuses=$2
    _crypte_dans_prompt=1
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
        _crypte_event after '' "$statuses" "$result" "$(builtin pwd -P)"
    elif (( _crypte_active && result == 130 )); then
        _crypte_event interrupt '' '' "$result" "$(builtin pwd -P)"
    fi
    _crypte_pending=0
    _crypte_ouverture=0
    return "$result"
}

_crypte_sortie_prompt() { _crypte_dans_prompt=0; }

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
    # Toute commande avant le premier retour à l'invite appartient encore à la
    # ligne de démarrage (ex. crypte_commence; ls) et doit être observée.
    _crypte_ouverture=1
    _crypte_history
    _crypte_last_hid=$_crypte_hid
    ((_crypte_sequence+=1))
    _crypte_event start '' '' '' "$(builtin pwd -P)" "$_crypte_sequence" "$UID"
}

crypte_fin() {
    local resultat
    if (( ! _crypte_active )); then
        _crypte_event refused 'aucune tentative'
        return 1
    fi
    _crypte_event end '' '' '' "$(builtin pwd -P)"
    resultat=$?
    _crypte_active=0
    _crypte_pending=0
    _crypte_restaurer_historique
    return "$resultat"
}

_crypte_restaurer_historique() {
    HISTCONTROL=$_crypte_old_control
    HISTIGNORE=$_crypte_old_ignore
    HISTSIZE=$_crypte_old_size
    (( _crypte_old_history )) || set +o history
    (( _crypte_old_histexpand )) && set -o histexpand
    return 0
}

# Composer les hooks de confiance du shell, sans eval de données de joueurs.
if [[ ${_crypte_hooks_installes-0} != 1 || $(trap -p DEBUG) != *'_crypte_before '* ]]; then
    _crypte_hooks_installes=1
    _crypte_commandes=()
    for _crypte_commande in "${PROMPT_COMMAND[@]}"; do
        case $_crypte_commande in
            '_crypte_prompt "$?" "${PIPESTATUS[*]}"'|_crypte_sortie_prompt) ;;
            *) _crypte_commandes+=("$_crypte_commande") ;;
        esac
    done
    PROMPT_COMMAND=('_crypte_prompt "$?" "${PIPESTATUS[*]}"' "${_crypte_commandes[@]}" '_crypte_sortie_prompt')
    for _crypte_signal in DEBUG INT EXIT HUP; do
        _crypte_trap=$(trap -p "$_crypte_signal")
        _crypte_ancien=''
        if [[ -n $_crypte_trap ]]; then
            _crypte_trap=${_crypte_trap#trap -- }
            _crypte_trap=${_crypte_trap% *}
            eval "_crypte_ancien=$_crypte_trap"
        fi
        case $_crypte_signal in
            DEBUG) _crypte_nouveau='_crypte_before "$BASH_COMMAND" "$?"' ;;
            INT) _crypte_nouveau='_crypte_interrupt' ;;
            EXIT) _crypte_nouveau='_crypte_exit "$?"' ;;
            HUP) _crypte_nouveau='' ;;
        esac
        if [[ -n $_crypte_nouveau && $_crypte_ancien == *"$_crypte_nouveau"* ]]; then
            continue
        fi
        [[ -z $_crypte_ancien ]] || _crypte_nouveau+="; $_crypte_ancien"
        [[ $_crypte_signal != HUP ]] || _crypte_nouveau="${_crypte_ancien:+$_crypte_ancien; }exit 129"
        trap "$_crypte_nouveau" "$_crypte_signal"
    done
    unset _crypte_signal _crypte_trap _crypte_ancien _crypte_nouveau _crypte_commandes _crypte_commande
fi
