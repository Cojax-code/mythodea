"""Oracle : monter_niveau directement, sans import du backend."""
import json
import random
import sys

sys.path.insert(0, '/engine')
import progression

data = json.load(sys.stdin)
p = data['profile']
fiche = progression.nouvelles_caracteristiques(random.Random(0))
fiche.update(niveau=p['level'], nature=p['nature'], trait_inne=p['trait'],
             points_commandement=p['pc'], moral=p['morale'], etiquettes=p['labels'],
             evolutions_acquises=p.get('unlocked_evolutions', []), evolution_apprise=None,
             etat_zombie=p['zombie'], niveaux_zombie=p['zombie_levels'])
if 'active_slots' in p:
    fiche.update(emplacements_etiquettes_actives=p['active_slots'], niveau_etendard=p['banner_level'])
else:
    class Instinct:
        def randint(self, a, b):
            return b
    for _ in range(min(4, (p['level'] - p['zombie_levels']) // 5)):
        progression.progression_specifique(fiche, Instinct())
_, reward = progression.monter_niveau(fiche, random.Random(data['seed']))
if isinstance(reward, tuple):
    kind, value = reward
    kind = {'maitrise_commandement': 'commandement', 'force_caractere': 'moral',
            'etiquette_zombie': 'etiquette'}.get(kind, kind)
elif isinstance(reward, int):
    kind, value = 'unite', reward
else:
    kind, value = '', ''
print(json.dumps(dict(kind=kind, value=str(value))))
