"""Extrait uniquement les sources verrouillées, sans checkout ni modification du moteur."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'backend/engine.lock.json').read_text(encoding='utf-8'))


def prepare(source, destination):
    lock = json.loads((ROOT / "backend/engine.lock.json").read_text(encoding="utf-8"))
    destination = destination.resolve()
    if destination.exists():
        raise SystemExit(f"Destination déjà présente : {destination}. Choisir un nouveau dossier.")
    # Lire les blobs du commit, jamais les fichiers modifiés du working tree.
    contents = {}
    for name, digest in lock["files"].items():
        data = subprocess.check_output(["git", "-C", str(source), "show", f"{lock['commit']}:python/{name}"])
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit(f"Source non conforme au verrou : {name}")
        contents[name] = data
    destination.mkdir(parents=True)
    for name, data in contents.items():
        (destination / name).write_bytes(data)
    print(f"Moteur {lock['commit']} prêt : {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Dépôt local du moteur (lecture seule).")
    parser.add_argument("--destination", type=Path, default=ROOT / '.runtime' / f"engine-{LOCK['commit'][:7]}")
    args = parser.parse_args()
    if args.source:
        prepare(args.source, args.destination)
    else:
        with tempfile.TemporaryDirectory(prefix="mythodea-source-") as directory:
            source = Path(directory) / "engine"
            subprocess.run(["git", "clone", "--branch", "v2.0", "--single-branch", "--no-checkout",
                            "https://github.com/Cojax-code/mythodea.git", str(source)], check=True)
            prepare(source, args.destination)
