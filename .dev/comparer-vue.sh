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
    python3 - "$travail/reference.json" "$travail/resultat.json" <<'PY'
import json
import sys
from pathlib import Path
a, b = (json.loads(Path(p).read_text()) for p in sys.argv[1:])
identiques = [k for k in a if a[k] == b[k]]
print(f'{len(identiques)}/{len(a)} scénarios strictement identiques : ' + ', '.join(identiques))
for scenario in a:
    if a[scenario] == b[scenario]:
        continue
    print(scenario)
    for champ in a[scenario]:
        av, ap = a[scenario][champ], b[scenario][champ]
        if av == ap:
            continue
        if isinstance(av, dict) and isinstance(ap, dict):
            cles = sorted(k for k in av.keys() | ap.keys() if av.get(k) != ap.get(k))
            print(' ', champ, ':', ', '.join(cles))
        else:
            print(' ', champ, ': différent')
PY
    exit 1
fi
