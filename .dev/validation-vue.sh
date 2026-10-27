#!/bin/bash
set -eu

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
python3 -m py_compile python/soldats.py python/combats.py python/ordres_pipeline.py

case "${1:-cibles}" in
    complet)
        python3 -B -m unittest discover -s .dev/tests -v > "$travail/vue-complets.log" 2>&1 ||
            { tail -50 "$travail/vue-complets.log"; exit 1; }
        tail -5 "$travail/vue-complets.log"
        ;;
    root)
        python3 -B -m unittest discover -s .dev/tests -p test_participations_permissions.py -v > "$travail/vue-root.log" 2>&1 ||
            { tail -50 "$travail/vue-root.log"; exit 1; }
        tail -5 "$travail/vue-root.log"
        ;;
    cibles)
        python3 -B -m unittest discover -s .dev/tests -p 'test_*participants.py' -v > "$travail/vue-cibles.log" 2>&1 ||
            { tail -50 "$travail/vue-cibles.log"; exit 1; }
        tail -5 "$travail/vue-cibles.log"
        ;;
    *)
        echo 'Usage : validation-vue.sh [cibles|complet|root]' >&2
        exit 2
        ;;
esac
