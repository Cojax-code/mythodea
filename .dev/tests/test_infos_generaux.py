"""Arborescence publique, migration sans perte et cycle inchangé."""
import os
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

import test_mythodea
import test_generations_survie
import progression


class InfosGeneraux(unittest.TestCase):
    setUp = test_mythodea.Regressions.setUp
    general = test_mythodea.Regressions.general

    def ancien(self):
        g = self.general()
        for fichier in (g / 'info').iterdir():
            fichier.rename(g / fichier.name)
        (g / 'info').rmdir()
        (g / 'fiche.txt').write_text(
            'nom=general1\nevolution_apprise=201\nevolutions_acquises=104,108\n'
            'position_surnombre=6\n', encoding='utf-8')
        return g

    def test_creation_racine_et_fiche_publique(self):
        g = self.general()
        self.assertEqual({p.name for p in g.iterdir()}, {*self.config.ordre_blocs, 'info'})
        fiche = self.generaux.lire_fiche_general(g)
        self.assertEqual(fiche['debloque'], '')
        self.assertEqual(fiche['apprentissage_niveau_suivant'], '')
        self.assertNotIn('evolution_apprise', fiche)
        self.assertNotIn('evolutions_acquises', fiche)

    def test_migration_tous_fichiers_et_dossiers_sans_toucher_aux_blocs(self):
        g = self.ancien()
        (g / '.notes').mkdir()
        (g / '.notes/a.txt').write_bytes(b'notes personnelles')
        (g / 'ordre_surnombre.txt').write_text('2\n')
        (g / 'avant/infanterie1').mkdir()
        (g / 'avant/infanterie1/pique').touch()
        avant = {str(p.relative_to(g)): (p.stat().st_ino, p.read_bytes())
                 for bloc in self.config.ordre_blocs for p in (g / bloc).rglob('*') if p.is_file()}
        prive = (self.config.game_path / '.systeme/progression.json').read_bytes()
        inode = (g / '.notes/a.txt').stat().st_ino
        self.assertTrue(self.generaux.est_general_valide(g))
        self.assertEqual(self.generaux.lire_fiche_general(g)['apprentissage_niveau_suivant'], '201')
        self.generaux.migrer_infos_general(g)
        self.generaux.migrer_infos_general(g)
        self.assertEqual({p.name for p in g.iterdir()}, {*self.config.ordre_blocs, 'info'})
        self.assertEqual((g / 'info/.notes/a.txt').stat().st_ino, inode)
        self.assertEqual((g / 'info/.notes/a.txt').read_bytes(), b'notes personnelles')
        self.assertEqual(self.generaux.lire_fiche_general(g)['debloque'], '104,108')
        self.assertEqual(self.generaux.lire_fiche_general(g)['position_surnombre'], '6')
        self.assertEqual((self.config.game_path / '.systeme/progression.json').read_bytes(), prive)
        for relatif, infos in avant.items():
            self.assertEqual(((g / relatif).stat().st_ino, (g / relatif).read_bytes()), infos)

    def test_collision_refusee_avant_tout_deplacement(self):
        g = self.ancien()
        (g / 'info').mkdir()
        (g / 'info/fiche.txt').write_text('autre fiche')
        (g / 'a.txt').write_text('a conserver')
        with self.assertRaisesRegex(RuntimeError, 'Doublon'):
            self.generaux.migrer_infos_general(g)
        self.assertEqual((g / 'a.txt').read_text(), 'a conserver')
        self.assertEqual((g / 'info/fiche.txt').read_text(), 'autre fiche')
        with self.assertRaisesRegex(RuntimeError, 'Doublon'):
            self.generaux.lire_fiche_general(g)

    def test_champs_contradictoires_refuses_sans_perte(self):
        g = self.ancien()
        fiche = g / 'fiche.txt'
        with fiche.open('a') as f:
            f.write('apprentissage_niveau_suivant=202\n')
        avant = fiche.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'contradictoires'):
            self.generaux.migrer_infos_general(g)
        self.assertEqual(fiche.read_bytes(), avant)
        self.assertFalse((g / 'info').exists())

    def test_interruption_entre_renommages_reprise_idempotente(self):
        g = self.ancien()
        (g / 'a.txt').write_text('personnel')
        original = type(g).rename
        def interrompre(source, destination):
            if source.name == 'fiche.txt':
                raise OSError('interruption')
            return original(source, destination)
        with patch.object(type(g), 'rename', interrompre):
            with self.assertRaisesRegex(OSError, 'interruption'):
                self.generaux.migrer_infos_general(g)
        self.assertEqual((g / 'info/a.txt').read_text(), 'personnel')
        self.assertTrue(self.generaux.est_general_valide(g))
        self.generaux.migrer_infos_general(g)
        self.assertEqual(self.generaux.lire_fiche_general(g)['debloque'], '104,108')

    @unittest.skipIf(os.name == 'nt', 'Liens Linux requis')
    def test_liens_et_info_non_dossier_refuses(self):
        for genre in ('symbolique', 'physique', 'info'):
            with self.subTest(genre=genre):
                g = self.ancien()
                cible = self.chemin('/home/j1/secret.txt')
                cible.write_text('secret')
                lien = g / ('info' if genre == 'info' else 'QG.txt')
                if genre == 'physique':
                    os.link(cible, lien)
                elif genre == 'info':
                    lien.write_text('collision')
                else:
                    lien.symlink_to(cible)
                with self.assertRaises(RuntimeError):
                    self.generaux.migrer_infos_general(g)
                self.assertEqual(cible.read_text(), 'secret')
                lien.unlink()
                self.generaux.migrer_infos_general(g)

    def test_ancienne_memoire_remplace_la_meme_recompense(self):
        g = self.general()
        fiche = progression.charger()['j1:general1']
        fiche.update(nature='stratege', points_commandement=13,
                     evolution_apprise=201, evolutions_acquises=[104])
        progression.sauvegarder({'j1:general1': fiche})
        progression.publier_fiche(g, fiche)
        self.assertEqual(self.generaux.lire_fiche_general(g)['apprentissage_niveau_suivant'], '201')
        attendu, recompense = progression.monter_niveau(fiche, random.Random(42))
        obtenu = progression.attribuer_niveau(dict(joueur='j1', nom='general1', chemin=g), random.Random(42))
        self.assertEqual(obtenu, recompense)
        self.assertEqual(progression.charger()['j1:general1'], json.loads(json.dumps(attendu)))
        self.assertEqual(self.generaux.lire_fiche_general(g)['apprentissage_niveau_suivant'], '')


class CycleInfos(unittest.TestCase):
    setUp = test_generations_survie.GenerationsSurvie.setUp
    general = test_generations_survie.GenerationsSurvie.general
    gestion = test_generations_survie.GenerationsSurvie.gestion
    activer = test_generations_survie.GenerationsSurvie.activer

    def test_migration_couvre_toutes_zones_et_acteurs(self):
        anciens = []
        for joueur in self.profil['acteurs']:
            for zone in self.generaux.zones_generaux(joueur, self.profil):
                g = zone['chemin'] / 'general9001'
                g.mkdir(parents=True, exist_ok=True)
                for bloc in self.config.ordre_blocs:
                    (g / bloc).mkdir(exist_ok=True)
                (g / 'fiche.txt').write_text('nom=general9001\nevolutions_acquises=104\n')
                anciens.append(g)
        self.generaux.migrer_infos_generaux(self.profil)
        for g in anciens:
            with self.subTest(general=g):
                self.assertEqual({p.name for p in g.iterdir()}, {*self.config.ordre_blocs, 'info'})
                self.assertEqual(self.generaux.lire_fiche_general(g)['debloque'], '104')

    def test_initialisation_silencieuse_gel_et_bienvenue_conserves(self):
        gestion = self.gestion()
        gestion.initialiser_exploration()
        self.assertEqual(self.gel.evenements, [('gel', None), ('degel', None)])
        gestion.annoncer_debut()
        self.assertEqual(self.gel.evenements[-1][0], 'annonce')

    def test_ancien_general_capture_publication_et_double_annonce(self):
        g = self.general(territoire='home')
        for fichier in (g / 'info').iterdir():
            fichier.rename(g / fichier.name)
        (g / 'info').rmdir()
        (g / 'notes.txt').write_text('mes notes')
        gestion = self.gestion()
        self.survie.resoudre_tour_survie(self.profil, random.Random(4), gestion)
        self.assertEqual((g / 'info/notes.txt').read_text(), 'mes notes')
        self.assertEqual({p.name for p in g.iterdir()}, {*self.config.ordre_blocs, 'info'})
        annonces = [m for action, m in self.gel.evenements if action == 'annonce']
        self.assertTrue(annonces[0].startswith('FIN DES ACTIONS'))
        self.assertTrue(annonces[1].startswith('PUBLICATION DU TOUR'))
        self.assertEqual(sum(action == 'gel' for action, _ in self.gel.evenements), 2)
        for etape in ('capture', 'travail'):
            self.assertEqual((gestion.generation / etape / 'homes/j1/general1/info/notes.txt').read_text(), 'mes notes')
