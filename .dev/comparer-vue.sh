#!/bin/bash
set -euo pipefail

# Racine des sources : indépendante du chemin Windows/WSL et de /game.
source_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
reference=980a3d70a2a1382a75c60b65f26fe22cc2607c24
travail=$(mktemp -d /tmp/mythodea-comparaison-XXXXXX)
trap 'rm -rf -- "$travail"' EXIT

mkdir -p "$travail/avant" "$travail/apres"
git -C "$source_repo" cat-file -e "$reference^{commit}"
git -C "$source_repo" archive "$reference" | tar -xf - -C "$travail/avant"
git -C "$source_repo" -c core.quotepath=false ls-files -z | (
    cd "$source_repo"
    tar --null -T - -cf -
) | tar -xf - -C "$travail/apres"

# Même outil de comparaison dans les deux copies.
cp "$source_repo/.dev/comparer-vue.py" "$travail/avant/.dev/comparer-vue.py"

cd "$travail/avant"
PYTHONPYCACHEPREFIX="$travail/cache-avant" python3 -B .dev/comparer-vue.py "$travail/reference.json"
cd "$travail/apres"
PYTHONPYCACHEPREFIX="$travail/cache-apres" python3 -B .dev/comparer-vue.py "$travail/resultat.json"

if cmp -s "$travail/reference.json" "$travail/resultat.json"; then
    echo '30 scénarios identiques entre 980a3d7 et les sources actuelles (hors inodes et racines temporaires).'
else
    echo 'Différence de résultats : comparaison échouée.' >&2
    diff -u "$travail/reference.json" "$travail/resultat.json" | cut -c1-350 | head -60 || true
    exit 1
fi
