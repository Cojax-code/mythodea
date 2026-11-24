"""Génération indépendante : appels directs au moteur monté par Bubblewrap."""
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, '/engine')
import progression

payload = json.load(sys.stdin)
rng = random.Random(payload['seed'])
fiche = progression.nouvelles_caracteristiques(rng)
for _ in range(payload['level']):
    fiche, _ = progression.monter_niveau(fiche, rng)
fiche = progression.selection_etiquettes(fiche, Path('/game'))
print(json.dumps({'profile': {
    'level': fiche['niveau'], 'nature': fiche['nature'], 'trait': fiche['trait_inne'],
    'pc': fiche['points_commandement'], 'morale': fiche['moral'],
    'labels': fiche['etiquettes'], 'permanent': [],
    'active': fiche['etiquettes_actives'], 'zombie': False, 'zombie_levels': 0},
    'unlocked_evolutions': fiche['evolutions_acquises']}))
