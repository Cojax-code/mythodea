#!/bin/bash

set -euo pipefail

refuser() {
    printf 'Erreur : %s\n' "$*" >&2
    exit 1
}

echo '=== Reset Mythodea Survie ==='
echo '[1/7] Vérification root'
[[ $EUID -eq 0 ]] || refuser 'Utiliser sudo bash bash/reset_survie.sh (root requis).'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd -- "$PROJECT_DIR"
source "$SCRIPT_DIR/stockage.sh"

for commande in python3 getent id useradd groupadd usermod install rm find ps findmnt; do
    command -v "$commande" >/dev/null || refuser "Commande requise absente : $commande"
done
[[ -f "$PROJECT_DIR/python/crypte_installer.py" ]] || refuser 'Installateur Crypte absent.'

verifier_arret() {
    local chemin joueur uid fichier processus
    for chemin in /home /home/j1 /home/j2 /home/.mythodea-publication "$GAME_PATH/.systeme" "$GAME_PATH/systeme"; do
        [[ ! -L "$chemin" ]] || refuser "Lien symbolique interdit : $chemin"
        if [[ -e "$chemin" && ! -d "$chemin" ]]; then
            refuser "Dossier attendu : $chemin"
        fi
    done
    for chemin in "$GAME_PATH/.systeme" "$GAME_PATH/systeme"; do
        if [[ -e "$chemin/gel_survie.json" || -L "$chemin/gel_survie.json" ]]; then
            refuser "Journal de gel présent : $chemin/gel_survie.json. Moteur arrêté, utiliser sudo python3 python/survie_admin.py degeler --confirmer puis refaire le diagnostic (outil de la version concernée pour systeme/)."
        fi
        # Un verrou résiduel exige lui aussi le diagnostic administratif commun.
        if [[ -e "$chemin/verrou_cycle_survie" || -L "$chemin/verrou_cycle_survie" ]]; then
            refuser "Un moteur Mythodea semble encore actif ($chemin/verrou_cycle_survie). Arrêtez-le proprement. Pour un verrou résiduel : diagnostic puis retirer-verrou --confirmer avec survie_admin.py de la version concernée."
        fi
    done
    processus="$(ps -eo args=)"
    if [[ "$processus" =~ (^|/|[[:space:]])mythodea_v_1_5[.]py([[:space:]]|$) ]]; then
        refuser 'Un moteur Mythodea semble encore actif. Arrêtez-le proprement avant le reset.'
    fi
    for joueur in j1 j2; do
        if getent passwd "$joueur" >/dev/null; then
            uid="$(id -u "$joueur")"
            [[ "$uid" =~ ^[0-9]+$ && "$uid" != 0 ]] || refuser "UID joueur invalide : $joueur"
            for chemin in /sys/fs/cgroup /sys/fs/cgroup/user.slice "/sys/fs/cgroup/user.slice/user-$uid.slice"; do
                fichier="$chemin/cgroup.freeze"
                if [[ -e "$fichier" && "$(cat -- "$fichier")" != 0 ]]; then
                    refuser "$joueur est gelé. Utiliser sudo python3 python/survie_admin.py degeler --confirmer puis refaire le diagnostic ; examiner aussi tout gel extérieur au moteur."
                fi
                fichier="$chemin/cgroup.events"
                if [[ -e "$fichier" && "$(cat -- "$fichier")" == *'frozen 1'* ]]; then
                    refuser "$joueur est encore gelé. Utiliser sudo python3 python/survie_admin.py degeler --confirmer puis refaire le diagnostic."
                fi
            done
        fi
    done
}

echo '[2/7] Vérification partition, moteur arrêté et joueurs dégelés'
verifier_stockage
verifier_arret
verifier_sous_montages
if [[ ! -f /sys/fs/cgroup/cgroup.controllers || ! -d /run/systemd/system ]]; then
    refuser 'Le mode Survie exige systemd actif et cgroup v2.'
fi
for commande in systemctl loginctl; do
    command -v "$commande" >/dev/null || refuser "Le mode Survie exige $commande."
done

echo '[3/7] Comptes et groupe'
for joueur in j1 j2; do
    if ! getent passwd "$joueur" >/dev/null; then
        useradd --create-home --shell /bin/bash "$joueur"
    fi
    if ! getent group "$joueur" >/dev/null; then
        groupadd "$joueur"
    fi
done
if ! getent group mythodea_allies >/dev/null; then
    groupadd mythodea_allies
fi
usermod -aG mythodea_allies j1
usermod -aG mythodea_allies j2

# Maintenance administrative : aucun lancement ni changement de montage concurrent.
verifier_arret
verifier_stockage
# Réserver le même fichier exclusif que etat.verrou_cycle_survie(). Ne pas l'effacer
# pendant le nettoyage : un moteur Survie démarrant entre les contrôles sera refusé.
install -d -o root -g mythodea_allies -m 710 "$GAME_PATH/.systeme"
if ! (umask 077; set -o noclobber; printf '%s\n' "$$" > "$GAME_PATH/.systeme/verrou_cycle_survie") 2>/dev/null; then
    refuser 'Verrou apparu pendant les contrôles : reset annulé, arrêter le moteur.'
fi
liberer_verrou_reset() {
    if [[ -f "$GAME_PATH/.systeme/verrou_cycle_survie" && "$(cat -- "$GAME_PATH/.systeme/verrou_cycle_survie")" == "$$" ]]; then
        rm -f -- "$GAME_PATH/.systeme/verrou_cycle_survie"
    fi
}
trap liberer_verrou_reset EXIT
echo '[4/7] Suppression du contenu du plateau'
echo "Destruction complète de la partie Survie actuelle dans $GAME_PATH ; partition conservée."
vider_plateau conserver_verrou_survie

echo '[5/7] Nettoyage des généraux uniquement'
rm -rf --one-file-system -- /home/j1/general* /home/j2/general*
install -d -o j1 -g j1 -m 700 /home/j1
install -d -o j2 -g j2 -m 700 /home/j2

echo '[6/7] Permissions et racines système'
chown root:root "$GAME_PATH"
chmod 755 "$GAME_PATH"
install -d -o root -g mythodea_allies -m 710 "$GAME_PATH/.systeme"
install -d -o root -g root -m 700 /home/.mythodea-publication

echo '[7/7] Installation Crypte et vérification de structure'
python3 "$PROJECT_DIR/python/crypte_installer.py"
python3 -B - "$PROJECT_DIR/python" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import config
config.verifier_structure_actuelle(config.configuration_mode('survie'))
PY

echo '=== Reset Survie terminé ==='
echo 'Lancer :'
echo 'bash bash/start.sh --mode survie'
echo "Reconnecter les sessions SSH j1/j2 si leur appartenance au groupe mythodea_allies vient d'être modifiée, et pour charger les hooks Crypte réinstallés."
