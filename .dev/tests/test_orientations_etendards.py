"""Refonte des trois orientations et protections territoriales individuelles."""
from copy import deepcopy
import itertools
import json
import os
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import Mock, patch

import test_soldats_formation as support
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import progression
import catalogues
import commandement
import etendards


class Orientations(unittest.TestCase):
    def fiche(self, nature='hybride', **champs):
        fiche = progression.nouvelles_caracteristiques(random.Random(1))
        fiche.update(nature=nature, **champs)
        return fiche

    def test_creation_trois_orientations_et_traits_exacts(self):
        comptes = dict.fromkeys(('stratege', 'instinctif', 'hybride'), 0)
        for ticket in range(1, 101):
            f = progression.nouvelles_caracteristiques(Mock(randint=Mock(side_effect=[ticket, 1])))
            comptes[f['nature']] += 1
            self.assertNotIn('orientation_principale', f)
            self.assertEqual((f['niveau'], f['points_commandement'], f['moral']), (0, 0, 0))
            self.assertEqual((f['emplacements_etiquettes_actives'], f['niveau_etendard']), (1, 0))
        self.assertEqual(comptes, dict(stratege=45, instinctif=45, hybride=10))
        for nature, nature_ticket, attendus in (
                ('stratege', 1, (50, 35, 15)), ('instinctif', 46, (50, 15, 35)),
                ('hybride', 91, (50, 25, 25))):
            compte = dict.fromkeys(('charismatique', 'leader', 'inventeur'), 0)
            for ticket in range(1, 101):
                f = progression.nouvelles_caracteristiques(Mock(randint=Mock(side_effect=[nature_ticket, ticket])))
                compte[f['trait_inne']] += 1
            self.assertEqual(tuple(compte.values()), attendus)

    def test_tous_les_enchainements_hybrides_et_supplements_sans_limite(self):
        for tirages in itertools.product((1, 100), repeat=4):
            f = self.fiche()
            for indice, ticket in enumerate(tirages, 1):
                f.update(niveau=indice * 5 - 1, evolution_apprise=201)
                avant = deepcopy(f)
                rng = Mock(randint=lambda a, b: ticket if (a, b) == (1, 100) else a)
                f, classique = progression.monter_niveau(f, rng)
                self.assertEqual(classique, ('maitrise_commandement', 5))
                self.assertEqual(f['points_commandement'] - avant['points_commandement'], 7)
                self.assertEqual(f['etiquettes'], {})
                self.assertEqual((f['emplacements_etiquettes_actives'] - 1) + f['niveau_etendard'], indice)
                self.assertEqual(f['dernier_niveau']['classique'], classique)
                self.assertIsNotNone(f['dernier_niveau']['supplementaire'])
                self.assertIsNone(f['evolution_apprise'])
            self.assertEqual((f['emplacements_etiquettes_actives'], f['niveau_etendard']), (3, 2))
            for niveau in (25, 30, 55, 100):
                f.update(niveau=niveau - 1, evolution_apprise=201)
                avant_pc = f['points_commandement']
                f, classique = progression.monter_niveau(f, Mock(randint=lambda a, b: a))
                self.assertEqual(f['points_commandement'] - avant_pc, 12)
                self.assertEqual(f['dernier_niveau']['supplementaire'], ('maitrise_commandement', 5))

    def test_hybride_premier_etendard_tardif_et_basculement(self):
        f = self.fiche(niveau=14, emplacements_etiquettes_actives=3, evolution_apprise=201)
        f, _ = progression.monter_niveau(f, Mock(randint=lambda a, b: a))
        self.assertEqual(f['niveau_etendard'], 1)
        self.assertEqual(f['dernier_niveau']['basculement'], 'stratege → instinctif')
        f.update(niveau=24, evolution_apprise=201)
        f, _ = progression.monter_niveau(f, Mock(randint=lambda a, b: a))
        self.assertEqual(f['dernier_niveau']['supplementaire'], ('etendard', 2))

    def test_stratege_instinctif_classique_et_capacite_sans_etiquette(self):
        for nature in ('stratege', 'instinctif'):
            f = self.fiche(nature)
            for niveau in (5, 10, 15, 20, 25, 30):
                f.update(niveau=niveau - 1, evolution_apprise=201 if nature == 'stratege' else 202)
                avant = deepcopy(f)
                f, classique = progression.monter_niveau(f, Mock(randint=lambda a, b: a))
                self.assertEqual(f['dernier_niveau']['classique'], classique)
                self.assertEqual(f['etiquettes'], {})
                attendu = ('emplacement_actif', 1 + niveau // 5) if nature == 'stratege' else ('etendard', niveau // 5)
                if niveau <= 10:
                    self.assertEqual(f['dernier_niveau']['supplementaire'], attendu)
                else:
                    self.assertEqual(f['dernier_niveau']['supplementaire'], ('maitrise_commandement', 5))
                self.assertEqual(f['dernier_niveau']['gains_naturels']['points_commandement'],
                                 2 if nature == 'stratege' else 0)
            self.assertEqual(f['emplacements_etiquettes_actives'], 3 if nature == 'stratege' else 1)

    def test_acces_croise_unites_ecole_roulette_et_qg(self):
        f = self.fiche()
        for apprentissage in (False, True):
            accessibles = progression.evolutions_eligibles(f, apprentissage=apprentissage)
            self.assertTrue({104, 107, 108, 109, 110, 201, 202} <= accessibles.keys())
        self.assertTrue(commandement.qg_autorise(f))
        import formation
        f['evolutions_acquises'] = [104]
        formation.verifier_acces_forge(f)

    def test_zombie_aucun_gain_naturel_classique_ou_specifique(self):
        for nature in progression.NATURES:
            f = self.fiche(nature, niveau=24, etat_zombie=True, niveaux_zombie=2,
                           etiquettes={'mort_vivant': 1}, evolution_apprise=201)
            apres, gain = progression.monter_niveau(f, Mock(randint=Mock(side_effect=AssertionError)))
            self.assertIsNone(gain)
            self.assertEqual(apres['niveaux_zombie'], 3)
            for champ in ('points_commandement', 'moral', 'niveau_etendard', 'emplacements_etiquettes_actives', 'evolution_apprise'):
                self.assertEqual(apres[champ], f[champ])
            self.assertNotIn('dernier_niveau', apres)


class Etendards(unittest.TestCase):
    setUp = support.SoldatsFormation.setUp
    activer = support.SoldatsFormation.activer
    general = support.SoldatsFormation.general
    modules = support.SoldatsFormation.modules
    creer = support.SoldatsFormation.creer
    infos = support.SoldatsFormation.infos

    def porteur(self, niveau=1, nombre=2, nature='instinctif'):
        g = self.creer(nombre=nombre, nature=nature)
        profils = progression.charger()
        profils['j1:general1'].update(niveau=10, niveau_etendard=niveau, moral=0)
        progression.sauvegarder(profils)
        (g['chemin'] / 'avant/etendard.txt').write_text('royal=999', encoding='utf-8')
        # Les scénarios de consommation imposent un succès ; la distribution
        # réelle et les échecs sont vérifiés séparément sur les cent tickets.
        self.enterContext(patch.object(self.combats.random, 'randint', return_value=1))
        return g

    def test_probabilites_exactes_charges_et_echec_sans_consommation(self):
        g = self.porteur(nombre=1)
        u = self.infos(g)['unites'][0]
        for niveau, taux, charges in ((1, 30, 1), (2, 50, 2)):
            profils = progression.charger()
            profils['j1:general1']['niveau_etendard'] = niveau
            progression.sauvegarder(profils)
            reussites = 0
            for ticket in range(1, 101):
                with etendards.guerre():
                    rng = Mock(randint=Mock(return_value=ticket))
                    succes = etendards.proteger(g, u, 'archer', rng)
                    reussites += succes
                    rng.randint.assert_called_once_with(1, 100)
                    self.assertEqual(next(iter(etendards.figer(g)['restantes'].values())), charges - int(succes))
            self.assertEqual(reussites, taux)
            with etendards.guerre():
                self.assertFalse(etendards.proteger(g, u, 'archer', Mock(randint=lambda a,b: 100)))
                for _ in range(charges):
                    self.assertTrue(etendards.proteger(g, u, 'archer', Mock(randint=lambda a,b: 1)))
                rng = Mock(randint=Mock(side_effect=AssertionError('Aucun tirage sans charge')))
                self.assertFalse(etendards.proteger(g, u, 'archer', rng))

    def test_echec_etendard_applique_la_perte_et_moral_reussi_ne_tire_pas(self):
        g = self.porteur(nombre=1)
        profils = progression.charger()
        profils['j1:general1']['moral'] = 100
        progression.sauvegarder(profils)
        with etendards.guerre():
            with patch.object(self.combats.random, 'randint', side_effect=AssertionError('Moral prioritaire')):
                self.assertEqual(self.combats.supprimer_unites(self.infos(g), 0, g), [])
            with patch.object(self.combats.random, 'randint', return_value=100):
                self.assertEqual(len(self.combats.supprimer_unites(self.infos(g), 0, g)), 1)

    def test_protection_individuelle_sans_moral_normale_et_royale(self):
        g = self.porteur(niveau=2)
        with etendards.guerre():
            for _ in range(2):
                self.assertEqual(self.combats.supprimer_unites(self.infos(g), 0, g), [])
                self.assertEqual(self.infos(g)['nombre'], 2)
            self.assertEqual(len(self.combats.supprimer_unites(self.infos(g), 0, g)), 2)
        self.assertFalse((g['chemin'] / 'avant/etendard.txt').exists())
        self.assertEqual(progression.charger()['j1:general1']['niveau_etendard'], 2)

    def test_moral_prioritaire_cumul_veteran_sans_blessure_de_protection(self):
        g = self.porteur(niveau=1, nombre=1)
        u = self.infos(g)['unites'][0]
        for i in range(5):
            self.soldats.terminer_bataille([u], f'ancien:{i}')
        profils = progression.charger()
        profils['j1:general1']['moral'] = 100
        progression.sauvegarder(profils)
        with etendards.guerre():
            for blessures in (1, 2):
                self.assertEqual(self.combats.supprimer_unites(self.infos(g), 0, g), [])
                self.assertEqual(int((u / 'blessures.txt').read_text()), blessures)
                self.assertEqual(next(iter(etendards.figer(g)['restantes'].values())), 1)
            self.assertEqual(self.combats.supprimer_unites(self.infos(g), 0, g), [])
            self.assertEqual(int((u / 'blessures.txt').read_text()), 2)
            self.assertEqual(len(self.combats.supprimer_unites(self.infos(g), 0, g)), 1)

    def test_pas_de_partage_entre_unites_ni_blocs_et_aucune_perte_hors_combat(self):
        g = self.porteur()
        infos = self.infos(g)
        un, deux = infos['unites']
        autre_bloc = g['chemin'] / 'droite/infanterie9'
        autre_bloc.mkdir()
        (autre_bloc / 'arc').touch()
        with etendards.guerre():
            etendards.figer(g)
            for _ in range(2):
                self.combats.supprimer_unites(dict(nombre=1, type='archer', unites=[un]), 0, g)
            self.assertFalse(un.exists())
            self.assertTrue(deux.exists())
            self.assertEqual(self.combats.supprimer_unites(dict(nombre=1, type='archer', unites=[deux]), 0, g), [])
            pertes = self.combats.supprimer_unites(dict(nombre=1, type='archer', unites=[autre_bloc]), 0, g)
            self.assertEqual(len(pertes), 1)
            self.assertTrue(deux.exists())

    def test_renouvellement_uniquement_guerre_suivante_et_pas_de_soin(self):
        g = self.porteur(nombre=1)
        u = self.infos(g)['unites'][0]
        self.soldats.pertes(self.infos(g), 0, moral=100)
        with etendards.guerre():
            self.assertEqual(self.combats.supprimer_unites(self.infos(g), 0, g), [])
            with etendards.guerre():
                self.assertEqual(next(iter(etendards.figer(g)['restantes'].values())), 0)
            marqueur = g['chemin'] / 'avant/etendard.txt'
            marqueur.unlink()
            marqueur.touch()
            self.assertEqual(next(iter(etendards.figer(g)['restantes'].values())), 0)
        with etendards.guerre():
            self.assertEqual(self.combats.supprimer_unites(self.infos(g), 0, g), [])
            self.assertEqual(int((u / 'blessures.txt').read_text()), 1)

    def test_absence_figee_et_reconstruction_seulement_prochaine_guerre(self):
        g = self.porteur(nombre=1)
        marqueur = g['chemin'] / 'avant/etendard.txt'
        with etendards.guerre():
            for _ in range(2):
                self.combats.supprimer_unites(self.infos(g), 0, g)
            self.assertFalse(marqueur.exists())
            u = g['chemin'] / 'avant/infanterie9'
            u.mkdir()
            (u / 'arc').touch()
            marqueur.touch()
            self.assertFalse(etendards.proteger(g, u, 'archer'))
        with etendards.guerre():
            self.assertTrue(etendards.proteger(g, u, 'archer'))
        marqueur.unlink()
        with etendards.guerre():
            self.assertIsNone(etendards.figer(g))
            marqueur.touch()
            self.assertFalse(etendards.proteger(g, u, 'archer'))

    def test_declarations_capacite_officielle_doublons_et_faux_royal(self):
        g = self.porteur(nombre=1)
        self.assertEqual(etendards.declaration(g), ('avant', 1))
        with (g['chemin'] / 'fiche.txt').open('a') as f:
            f.write('\nniveau_etendard=2\nemplacements_etiquettes_actives=99\n')
        self.assertEqual(etendards.declaration(g), ('avant', 1))
        self.assertEqual(progression.caracteristiques_general(g)['emplacements_etiquettes_actives'], 1)
        double = g['chemin'] / 'droite/etendard.txt'
        double.touch()
        with self.assertRaises(ValueError):
            etendards.declaration(g)
        double.unlink()
        profils = progression.charger()
        profils['j1:general1']['niveau_etendard'] = 0
        progression.sauvegarder(profils)
        with self.assertRaises(ValueError):
            etendards.declaration(g)

    def test_liens_et_objets_speciaux_refuses_avant_copie(self):
        import cycle_linux
        g = self.porteur()
        marqueur = g['chemin'] / 'avant/etendard.txt'
        marqueur.unlink()
        cible = g['chemin'] / 'source'
        cible.touch()
        for genre in ('lien', 'hardlink', 'dossier', 'fifo'):
            if genre == 'fifo' and not hasattr(os, 'mkfifo'):
                continue
            if genre == 'lien':
                marqueur.symlink_to(cible)
            elif genre == 'hardlink':
                os.link(cible, marqueur)
            elif genre == 'dossier':
                marqueur.mkdir()
            else:
                os.mkfifo(marqueur)
            try:
                with self.assertRaises(ValueError):
                    etendards.declaration(g)
                with self.assertRaises(RuntimeError):
                    cycle_linux.copier(marqueur, g['chemin'] / 'copie')
            finally:
                marqueur.rmdir() if genre == 'dossier' else marqueur.unlink()

    def test_hybride_qg_et_etendard_royal_remplace_normal(self):
        g = self.porteur(nature='hybride')
        (g['chemin'] / 'QG.txt').touch()
        territoire = g['chemin'].parents[2]
        with self.combats._contexte_qg_territorial(territoire, self.profil):
            self.assertEqual(etendards.figer(g)['niveau'], 1)
            self.assertIn(('j1', 'general1'), self.combats._EFFETS_TERRITOIRE.get()['qg'])
        profils = progression.charger()
        profils['j1:general1']['niveau_etendard'] = 2
        progression.sauvegarder(profils)
        with etendards.guerre():
            self.assertEqual(set(etendards.figer(g)['restantes'].values()), {2})

    def test_migration_unique_persistante_sans_perte_ni_roulette(self):
        g = self.creer(nature='hybride')
        profils = progression.charger()
        f = profils['j1:general1']
        f.update(nature='instinctif_hybride', orientation_principale='instinctif', niveau=25,
                 moral=42, points_commandement=76, etiquettes={'orc': 3}, evolutions_acquises=[107, 202])
        for cle in ('version_progression', 'niveau_etendard', 'emplacements_etiquettes_actives'):
            f.pop(cle, None)
        fichier = self.config.game_path / '.systeme/progression.json'
        fichier.write_text(json.dumps(profils), encoding='utf-8')
        unites = list(self.infos(g)['unites'])
        with patch.object(progression.aleatoire_progression, 'randint', return_value=100) as tirage:
            nouveau = progression.charger()['j1:general1']
            self.assertEqual(tirage.call_count, 4)
            apres = fichier.read_bytes()
            self.assertEqual(progression.charger()['j1:general1'], nouveau)
            self.assertEqual(tirage.call_count, 4)
            self.assertEqual(fichier.read_bytes(), apres)
        self.assertEqual((nouveau['nature'], nouveau['niveau_etendard'], nouveau['emplacements_etiquettes_actives']),
                         ('hybride', 2, 3))
        self.assertEqual((nouveau['moral'], nouveau['points_commandement'], nouveau['etiquettes'], nouveau['evolutions_acquises']),
                         (42, 76, {'orc': 3}, [107, 202]))
        self.assertEqual(self.infos(g)['unites'], unites)
        self.assertNotIn('orientation_principale', nouveau)
