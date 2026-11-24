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
    # Un instantané local reste verrouillé par ses empreintes, indépendamment
    # du commit de référence. Le mode commit conserve la lecture des blobs Git.
    contents = {}
    for name, digest in lock["files"].items():
        if lock.get('source_mode') == 'working-tree':
            data = (source / 'python' / name).read_text(encoding='utf-8').encode()
        else:
            data = subprocess.check_output(["git", "-C", str(source), "show", f"{lock['commit']}:python/{name}"])
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit(f"Source non conforme au verrou : {name}")
        contents[name] = data
    destination.mkdir(parents=True)
    for name, data in contents.items():
        (destination / name).write_bytes(data)
    print(f"Moteur {lock.get('snapshot', lock['commit'])} prêt : {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Dépôt local du moteur (lecture seule).")
    parser.add_argument("--destination", type=Path, default=ROOT / '.runtime' / f"engine-{LOCK.get('snapshot', LOCK['commit'])[:7]}")
    args = parser.parse_args()
    if args.source:
        prepare(args.source, args.destination)
    else:
        if LOCK.get('source_mode') == 'working-tree':
            parser.error('Cet instantané exige --source vers le dépôt local correspondant au verrou.')
        with tempfile.TemporaryDirectory(prefix="mythodea-source-") as directory:
            source = Path(directory) / "engine"
            subprocess.run(["git", "clone", "--branch", "v2.0", "--single-branch", "--no-checkout",
                            "https://github.com/Cojax-code/mythodea.git", str(source)], check=True)
            prepare(source, args.destination)
