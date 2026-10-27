#!/bin/bash
set -eu
source_repo='/mnt/c/Users/marti/1.cree_manuel/perso/OTW/linux/Mythodea/Mythodea_code'
travail=$(mktemp -d /tmp/mythodea-comparaison-XXXXXX)
trap 'rm -rf -- "$travail"' EXIT
mkdir "$travail/avant" "$travail/apres"
cd "$source_repo"
git archive HEAD | tar -xf - -C "$travail/avant"
git ls-files -z | tar --null -T - -cf - | tar -xf - -C "$travail/apres"
cp .dev/comparer-vue.py "$travail/avant/.dev/comparer-vue.py"
cp .dev/comparer-vue.py "$travail/apres/.dev/comparer-vue.py"
cd "$travail/avant"
python3 -B .dev/comparer-vue.py "$source_repo/.dev/vue-reference.json"
cd "$travail/apres"
python3 -B .dev/comparer-vue.py "$source_repo/.dev/vue-resultat.json"
cmp "$source_repo/.dev/vue-reference.json" "$source_repo/.dev/vue-resultat.json"
echo '30 scénarios avant/après strictement identiques (hors inodes et racines temporaires).'
