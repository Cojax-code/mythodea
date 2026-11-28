# Chargé après le scanner officiel par le script administrateur.
# _crypte_client et _crypte_socket sont fournis par ce script, pas par le joueur.
_crypte_token=''
_crypte_seq=0

_crypte_event() {
    local reponse resultat
    if [[ $1 == start ]]; then
        _crypte_seq=0
        _crypte_token=''
    else
        ((_crypte_seq+=1))
    fi
    reponse=$(/usr/bin/python3 "$_crypte_client" --socket "$_crypte_socket" \
        --session "$$" --token "$_crypte_token" --seq "$_crypte_seq" -- \
        "$1" "${2-}" "${3-}" "${4-}" "${5-}" "${6-}" "${7-}")
    resultat=$?
    if [[ $1 == start ]]; then
        if (( resultat )); then
            _crypte_active=0
            _crypte_restaurer_historique
            return "$resultat"
        fi
        _crypte_token=$reponse
        _mythodea_afficher 'Crypte : tentative ouverte.'
    elif [[ -n $reponse ]]; then
        _mythodea_afficher "Crypte : $reponse"
    fi
    return "$resultat"
}
