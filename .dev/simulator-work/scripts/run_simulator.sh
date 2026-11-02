#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

if [[ "$(uname -s)" != Linux ]] || ! command -v bwrap >/dev/null; then
    printf '%s\n' 'Linux et Bubblewrap sont nécessaires. Voir README.md.' >&2
    exit 1
fi

if [[ -x .venv/bin/python ]]; then
    exec .venv/bin/python -B -m backend.app
elif [[ -d .runtime/deps/flask ]]; then
    export PYTHONPATH="$PWD/.runtime/deps${PYTHONPATH:+:$PYTHONPATH}"
    exec python3 -B -m backend.app
else
    printf '%s\n' 'Préparer les dépendances Python selon README.md avant de lancer le serveur.' >&2
    exit 1
fi
