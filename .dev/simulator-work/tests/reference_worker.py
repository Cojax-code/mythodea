"""Oracle d'intégration : scénario monté séparément, appel direct au moteur officiel.

Ce fichier n'est monté que par les tests. Il ne réutilise pas l'adaptateur web.
"""
import json
from pathlib import Path
import random
import sys
import uuid
import contextlib

sys.path.insert(0, "/app")
from backend.worker import protect
protect()
sys.path.insert(0, "/engine")
import config
import etat
import generaux
import combats
import rapports
import progression
import soldats
import unites
import bouclier_vivant

payload = json.load(sys.stdin)
Path("/game/.systeme").mkdir()
territory = Path("/game/terrain1")
identities = random.Random(payload['seed'] ^ 0x1D3)
uuid.uuid4 = lambda: uuid.UUID(int=identities.getrandbits(128), version=4)
soldats.random = random.Random(payload['seed'] ^ 0x501D)
bouclier_vivant.random = random.Random(payload['seed'] ^ 0xB0C1)
progression.aleatoire_progression = random.Random(payload['seed'] ^ 0x1234)
paths = {}
positions = {}
for camp, owner in (("A", "j1"), ("B", "j2")):
    army = payload["armies"][camp]
    entries = army.get("generals", [{"position": 1, "order": "", "blocks": army.get("blocks")}])
    paths[camp] = []
    for index, entry in enumerate(entries, 1):
        name = f"general{index}"
        path = territory / owner / str(entry["position"]) / name
        path.mkdir(parents=True)
        (path / "fiche.txt").write_text(f"nom={name}\norientation=stratege\nstrategie=0\nforce=0\nexperience=0\n")
        if 'profile' in entry:
            p = entry['profile']
            fiche = progression.nouvelles_caracteristiques(random.Random(0))
            fiche.update(niveau=p['level'], nature=p['nature'], orientation_principale=p['nature'].removesuffix('_hybride'),
                         trait_inne=p['trait'], points_commandement=p['pc'], moral=p['morale'],
                         etiquettes=p['labels'], etiquettes_permanentes=p['permanent'],
                         etat_zombie=p['zombie'], niveaux_zombie=p['zombie_levels'])
            progression.enregistrer_creation(owner, name, fiche)
            progression.publier_fiche(path, fiche)
            (path / 'etiquettes_actives.txt').write_text('\n'.join(p['active']))
        if entry.get('qg'):
            (path / 'QG.txt').touch()
        for block in config.ordre_blocs:
            (path / block).mkdir()
            formation = entry["blocks"][block]
            counts = {formation['unit']: formation['count']}
            counts['messager_du_QG'] = counts.get('messager_du_QG', 0) + formation.get('messengers', 0)
            counts['Trop_gros_zombie'] = counts.get('Trop_gros_zombie', 0) + formation.get('shield', False)
            for unit_type, count in counts.items():
                for number in range(1, count + 1):
                    unit = path / block / f"{unites.definition(unit_type)['prefixe']}{number}"
                    unites.creer_officielle(unit, unit_type, {'simulateur': True})
                    if unit_type == 'messager_du_QG':
                        for item, mode in (('monocle', 0o700), ('sceau du roi', 0o070), ('enveloppe', 0o007)):
                            (unit/item).chmod(mode)
        paths[camp].append(path)
        positions[f"{owner}:{name}"] = territory.name
    etat.sauvegarder_compteur_general(owner, len(entries))
etat.sauvegarder_positions_generaux(positions)
etat.sauvegarder_generaux_fatigues(set())
combats.random = random.Random(payload["seed"])
generaux.random = random.Random(payload["seed"])
profile = config.configuration_mode("classique")
with soldats.bataille_complete('simulateur:terrain1', profile):
    if payload.get("mode", "OFF/OFF") == "OFF/DEF":
        combats.resoudre_combat_off_def(territory, {"A": "j1", "B": "j2"}[payload["defender"]], profile)
    else:
        combats.resoudre_combat_v15(territory, profile)
    unites.terminer_territoire(territory, 'simulateur:terrain1', profile)
unites.soigner_victoire_territoriale(profile, territory, 'simulateur:terrain1')
after = {}
for camp, entries in paths.items():
    states = [{"name": p.name, "position": int(p.parent.name), "alive": p.exists(),
               "blocks": generaux.lire_composition_general(p), "total": generaux.total_general_depuis_chemin(p)}
              for p in entries]
    if "blocks" in payload["armies"][camp]:
        after[camp] = {key: states[0][key] for key in ("alive", "blocks", "total")}
    else:
        after[camp] = {"generals": states, "total": sum(g["total"] for g in states),
                       "surviving_generals": sum(g["alive"] for g in states),
                       "destroyed_generals": sum(not g["alive"] for g in states)}
control = generaux.controle_forces(generaux.lire_forces_territoire(territory, profile))
print(json.dumps({"after": after, "control": control, "journal": config.rapport_long_path.read_text()}))
