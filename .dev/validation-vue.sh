#!/bin/bash
set -euo pipefail

if [ "${1:-cibles}" = root ] && [ "$(id -u)" -ne 0 ]; then
    echo 'Le mode root exige les privilèges Linux root réels.' >&2
    exit 2
fi

# Les tests travaillent sur une copie isolée et n'accèdent pas au /game monté.
source_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
travail=$(mktemp -d /tmp/mythodea-vue-XXXXXX)
trap 'rm -rf -- "$travail"' EXIT

git -C "$source_repo" ls-files -z | (
    cd "$source_repo"
    tar --null -T - -cf -
) | tar -xf - -C "$travail"

cd "$travail"
export PYTHONPYCACHEPREFIX="$travail/cache"
python3 -m py_compile python/soldats.py python/combats.py python/ordres_pipeline.py \
    .dev/tests/test_vue_participants.py .dev/tests/test_valeurs_combat.py \
    .dev/tests/test_participations_permissions.py .dev/comparer-vue.py

case "${1:-cibles}" in
    complet)
        python3 -B -m unittest discover -s .dev/tests -v > "$travail/vue-complets.log" 2>&1 ||
            { tail -50 "$travail/vue-complets.log"; exit 1; }
        tail -5 "$travail/vue-complets.log"
        ;;
    root)
        PYTHONPATH=.dev/tests python3 -B -m unittest -v \
            test_participations_permissions \
            test_crypte_scanner.ScannerCrypte.test_17_script_administrateur_non_modifiable \
            > "$travail/vue-root.log" 2>&1 ||
            { tail -50 "$travail/vue-root.log"; exit 1; }
        tail -5 "$travail/vue-root.log"
        ;;
    cibles)
        PYTHONPATH=.dev/tests python3 -B -m unittest -v \
            test_vue_participants test_valeurs_combat test_participations_temporaires \
            test_ordres_effets_v2 test_qg_effets_v2 > "$travail/vue-cibles.log" 2>&1 ||
            { tail -50 "$travail/vue-cibles.log"; exit 1; }
        tail -5 "$travail/vue-cibles.log"
        ;;
    *)
        echo 'Usage : validation-vue.sh [cibles|complet|root]' >&2
        exit 2
        ;;
esac
