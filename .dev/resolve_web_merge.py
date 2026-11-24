from pathlib import Path
import re

root = Path(__file__).resolve().parent
source = root / 'web-merge-review/merged'
target = root / 'simulator-work'
pattern = re.compile(r'^<<<<<<< [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n', re.M | re.S)
for path in source.rglob('*'):
    if not path.is_file():
        continue
    name = path.relative_to(source).as_posix()
    data = path.read_text(encoding='utf-8')
    index = [0]
    def resolve(match):
        index[0] += 1
        if name == 'js/simulateur.js':
            return match[2]
        if name == 'backend/profiles.py' and index[0] == 2:
            return match[2]
        if name == 'backend/schema.py':
            if index[0] == 1:
                return match[1].replace("'banner_level')", "'banner_level', 'unlocked_evolutions', 'corpse_available', 'quest_heavy_cavalry')") + match[2][match[2].index("    if 'unlocked_evolutions'"):]
            if index[0] == 2:
                return match[1].replace("'banner_block')", "'banner_block', 'qg_block')")
            return match[1] + match[2].replace("'stratege_hybride'", "'hybride'")
        return match[1]
    data = pattern.sub(resolve, data)
    if name == 'backend/profiles.py':
        data = data.replace("    try:\n        progression.capacite", "    fiche['evolutions_acquises'] = p.get('unlocked_evolutions', [])\n    try:\n        progression.capacite", 1)
        data = data.replace("'labels': fiche['etiquettes'], 'permanent': [],", "'labels': fiche['etiquettes'], 'permanent': [],\n        'active_slots': fiche['emplacements_etiquettes_actives'], 'banner_level': fiche['niveau_etendard'],")
    destination = target / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(data, encoding='utf-8', newline='\n')
print('Fusion locale préparée ; dépôt web inchangé.')

