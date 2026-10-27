"""Recette locale avant/après, sur les fixtures isolées existantes."""
import contextlib
import io
import itertools
import json
import random
import stat
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path[:0] = [str(Path('python').resolve()), str(Path('.dev/tests').resolve())]
import test_ordres_effets_v2 as aides


def nettoyer(valeur):
    if isinstance(valeur, dict):
        return {k: nettoyer(v) for k, v in valeur.items()
                if k not in ('inode', 'device', 'ino', 'dev')}
    if isinstance(valeur, list):
        return [nettoyer(v) for v in valeur]
    return valeur


resultats = {}
for graine in (0, 3, 17):
    for scenario in ('choc', 'manoeuvre', 'fatigue', 'moral', 'rafale',
                     'herisson', 'lourde', 'orcs', 'zombies', 'bouclier'):
        compte = itertools.count(1)
        random.seed(graine)
        with patch.object(uuid, 'uuid4', side_effect=lambda: uuid.UUID(int=next(compte))), \
                contextlib.redirect_stdout(io.StringIO()):
            t = aides.EffetsOrdres()
            t.setUp()
            try:
                t.generaux.aleatoire_caracteristiques.seed(graine)
                t.progression.aleatoire_progression.seed(graine)
                gauche = 'piquier'
                droite = 'cavalier'
                nombre = 8
                if scenario == 'lourde':
                    gauche, nombre = 'cavalerie_lourde', 15
                elif scenario == 'orcs':
                    gauche, droite = 'orc_assaillant', 'orc_chaman'
                elif scenario in ('zombies', 'bouclier'):
                    gauche, droite = 'zombie', 'archer'
                a = t.troupe('j1', gauche, nombre)
                b = t.troupe('j2', droite, 6, bloc='arriere' if scenario == 'manoeuvre' else 'avant')
                t.ordres(a, [1006] if scenario == 'herisson' else [],
                         moral=50 if scenario == 'moral' else 0)
                t.ordres(b, [1009] if scenario == 'rafale' else [])
                if scenario == 'fatigue':
                    t.etat.sauvegarder_generaux_fatigues({'j1:general1'})
                if scenario == 'rafale':
                    for n in range(8):
                        t.speciale(b, 'archer', n, 'arriere')
                if scenario == 'bouclier':
                    t.speciale(a, 'Trop_gros_zombie', 1, 'arriere')
                with t.soldats.bataille_complete('comparaison'):
                    r = t.combats.combat_entre_generaux(a, b)
                fichiers, droits = {}, {}
                for p in t.config.game_path.rglob('*'):
                    infos = p.stat()
                    droits[str(p.relative_to(t.config.game_path))] = (
                        infos.st_uid, infos.st_gid, stat.S_IMODE(infos.st_mode))
                    if p.is_file():
                        contenu = p.read_text(encoding='utf-8')
                        if p.suffix == '.json':
                            contenu = json.dumps(nettoyer(json.loads(contenu)), sort_keys=True)
                        fichiers[str(p.relative_to(t.config.game_path))] = contenu
                capture = json.dumps(dict(resultat=r, fichiers=fichiers, droits=droits, hasard=random.getstate(),
                    hasard_progression=t.progression.aleatoire_progression.getstate(),
                    hasard_caracteristiques=t.generaux.aleatoire_caracteristiques.getstate()),
                                     ensure_ascii=False, sort_keys=True, default=str)
                resultats[f'{scenario}:{graine}'] = json.loads(capture.replace(str(t.racine), '<partie>'))
            finally:
                t.doCleanups()
Path(sys.argv[1]).write_text(json.dumps(resultats, ensure_ascii=False, sort_keys=True), encoding='utf-8')
