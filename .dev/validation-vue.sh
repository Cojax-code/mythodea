#!/bin/bash
set -eu
source_repo='/mnt/c/Users/marti/1.cree_manuel/perso/OTW/linux/Mythodea/Mythodea_code'
travail=$(mktemp -d /tmp/mythodea-vue-XXXXXX)
trap 'rm -rf -- "$travail"' EXIT
cd "$source_repo"
git ls-files -z | tar --null -T - -cf - | tar -xf - -C "$travail"
for fichier in .dev/tests/test_vue_participants.py .dev/comparer-vue.py; do
    if [ -f "$fichier" ]; then cp "$fichier" "$travail/$fichier"; fi
done
cd "$travail"
export PYTHONPYCACHEPREFIX="$travail/cache"
python3 -m py_compile python/soldats.py python/combats.py python/ordres_pipeline.py
if [ "${1:-}" = complet ]; then
    python3 -B -m unittest discover -s .dev/tests -v > "$source_repo/.dev/vue-complets.log" 2>&1
    tail -5 "$source_repo/.dev/vue-complets.log"
elif [ "${1:-}" = root ]; then
    python3 -B -m unittest discover -s .dev/tests -p test_participations_permissions.py -v > "$source_repo/.dev/vue-root.log" 2>&1
    tail -5 "$source_repo/.dev/vue-root.log"
else
    python3 -B -m unittest discover -s .dev/tests -p 'test_*participants.py' -v > "$source_repo/.dev/vue-cibles.log" 2>&1
    tail -5 "$source_repo/.dev/vue-cibles.log"
fi
