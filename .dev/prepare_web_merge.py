"""Prépare une fusion révisable sans écrire dans le dépôt web voisin."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
local = root / '.dev/simulator-work'
web = root.parent / 'Mythodea_web'
review = root / '.dev/web-merge-review'
review.mkdir(exist_ok=True)
names = subprocess.check_output(['git', '-C', str(web), 'ls-files'], text=True).splitlines()
conflicts = []
for name in names:
    target = local / name
    remote = web / name
    if not remote.is_file():
        continue
    data = remote.read_bytes().replace(b'\r\n', b'\n')
    base = subprocess.run(['git', '-C', str(root), 'show', f'3391613:.dev/simulator-work/{name}'], capture_output=True)
    if not target.exists():
        result = data
    elif base.returncode:
        continue
    else:
        old = base.stdout.replace(b'\r\n', b'\n')
        if data == old:
            continue
        ours = target.read_bytes().replace(b'\r\n', b'\n')
        if ours == data:
            continue
        if ours == old:
            result = data
        else:
            for suffix, content in [('ours', ours), ('base', old), ('web', data)]:
                (review / suffix).write_bytes(content)
            merged = subprocess.run(['git', 'merge-file', '-p', str(review/'ours'), str(review/'base'), str(review/'web')], capture_output=True)
            result = merged.stdout
            if merged.returncode:
                conflicts.append(name)
    destination = review / 'merged' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result)
print('Conflits :', '\n'.join(conflicts))
print('Fichiers préparés :', len(list((review/'merged').rglob('*'))))
