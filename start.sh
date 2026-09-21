#!/bin/bash

set -euo pipefail

echo "=== Lancement Mythodea V1.5 ==="

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$SCRIPT_DIR"

# Le moteur affiche déjà le rapport court et les chemins des autres rapports.
if [[ $EUID -eq 0 ]]; then
    exec python3 "$SCRIPT_DIR/mythodea_v_1_5.py"
else
    exec sudo python3 "$SCRIPT_DIR/mythodea_v_1_5.py"
fi
