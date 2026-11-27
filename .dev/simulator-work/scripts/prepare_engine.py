"""Extrait uniquement les sources verrouillées, sans checkout ni modification du moteur."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'backend/engine.lock.json').read_text(encoding='utf-8'))


def prepare(source, destination, working_tree=False):
    lock = json.loads((ROOT / "backend/engine.lock.json").read_text(encoding="utf-8"))
    destination = destination.resolve()
    if destination.exists():
        raise SystemExit(f"Destination déjà présente : {destination}. Choisir un nouveau dossier.")
    local = lock.get('source_state') == 'working-tree'
    if local != working_tree:
        raise SystemExit('Ce verrou local exige --source et --working-tree ; un verrou officiel utilise les blobs Git.')
    if local:
        head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        if head != lock['commit']:
            raise SystemExit('La base Git locale ne correspond pas au verrou.')
    # Même en préparation locale explicite, chaque octet doit correspondre au verrou.
    contents = {}
    for name, digest in lock["files"].items():
        path = source / 'python' / name
        if local:
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise SystemExit(f'Source locale non ordinaire : {name}')
            data = path.read_bytes().replace(b'\r\n', b'\n')
        else:
            data = subprocess.check_output(["git", "-C", str(source), "show", f"{lock['commit']}:python/{name}"])
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit(f"Source non conforme au verrou : {name}")
        contents[name] = data
    destination.mkdir(parents=True)
    for name, data in contents.items():
        (destination / name).write_bytes(data)
    print(f"Moteur {lock.get('revision', lock['commit'])} prêt : {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Dépôt local du moteur (lecture seule).")
    parser.add_argument('--working-tree', action='store_true', help='Sources locales exactes du verrou, sans commit.')
    parser.add_argument("--destination", type=Path, default=ROOT / '.runtime' / f"engine-{LOCK.get('revision', LOCK['commit'][:7])}")
    args = parser.parse_args()
    if args.source:
        prepare(args.source, args.destination, args.working_tree)
    else:
        if args.working_tree or LOCK.get('source_state') == 'working-tree':
            parser.error('Les corrections sans commit exigent --source ../Mythodea_code --working-tree.')
        with tempfile.TemporaryDirectory(prefix="mythodea-source-") as directory:
            source = Path(directory) / "engine"
            subprocess.run(["git", "clone", "--branch", "v2.0", "--single-branch", "--no-checkout",
                            "https://github.com/Cojax-code/mythodea.git", str(source)], check=True)
            prepare(source, args.destination)
