"""Refonte des trois orientations et protections territoriales individuelles."""
from copy import deepcopy
import itertools
import json
import os
from pathlib import Path
import random
import shutil
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
    def setUp(self):
        support.SoldatsFormation.setUp(self)
        # Le support recharge config pour chaque plateau isolé.
        self.enterContext(patch.object(etendards, 'config', self.config))
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
        self.enterContext(patch.object(etendards.random, 'randint', return_value=1))
        return g

    def test_declaration_invalide_refusee_une_fois_sans_interrompre_territoire(self):
        g = self.porteur(nombre=2)
        (g['chemin'] / 'droite/etendard.txt').touch()
        territoire = g['chemin'].parents[2]
        with patch.object(self.rapports, 'noter_resultat') as rapport:
            with self.combats._contexte_qg_territorial(territoire, self.profil):
                self.assertIsNone(etendards.figer(g))
                self.assertEqual(len(self.combats.supprimer_unites(self.infos(g), 0, g)), 2)
                self.assertIsNone(etendards.figer(g))
            self.assertEqual(rapport.call_count, 1)
            self.assertIn('refusé', rapport.call_args.args[2])
        self.assertIsNone(etendards._guerre.get())

    def test_renommage_et_deplacement_general_conservent_les_charges(self):
        g = self.porteur(niveau=2, nombre=1)
        unite = self.infos(g)['unites'][0]
        with etendards.guerre():
            self.assertTrue(etendards.proteger(g, unite, 'archer'))
            renomme = unite.with_name('infanterie99')
            unite.rename(renomme)
            destination = g['chemin'].with_name('deplacement') / g['nom']
            destination.parent.mkdir()
            g['chemin'].rename(destination)
            g['chemin'] = destination
            unite = destination / 'avant' / renomme.name
            self.assertTrue(etendards.proteger(g, unite, 'archer'))
            self.assertFalse(etendards.proteger(g, unite, 'archer'))

    def test_remplacement_prive_conserve_uuid_et_aucune_recharge(self):
        g = self.porteur(niveau=2, nombre=1)
        unite = self.infos(g)['unites'][0]
        with etendards.guerre():
            self.assertTrue(etendards.proteger(g, unite, 'archer'))
            temporaire = unite.with_name('copie')
            shutil.copytree(unite, temporaire)
            shutil.rmtree(unite)
            temporaire.rename(unite)
            with patch.object(self.config, 'dans_generation_privee', return_value=True):
                self.assertTrue(etendards.proteger(g, unite, 'archer'))
                self.assertFalse(etendards.proteger(g, unite, 'archer'))

    def test_unite_remplacee_sans_identite_ne_vole_pas_de_charge(self):
        g = self.porteur(nombre=2)
        unite = self.infos(g)['unites'][0]
        with etendards.guerre():
            etendards.figer(g)
            registre = self.soldats.charger()
            identifiant = self.soldats.retrouver(unite, registre)
            registre[identifiant]['detruit'] = True
            self.soldats.sauvegarder(registre)
            shutil.rmtree(unite)
            unite.mkdir()
            (unite / 'arc').touch()
            self.assertFalse(etendards.proteger(g, unite, 'archer'))

    def test_zombies_et_bouclier_exclus_sans_tirage(self):
        g = self.porteur(nombre=1)
        unite = self.infos(g)['unites'][0]
        rng = Mock(randint=Mock(side_effect=AssertionError('Zombie protégé')))
        with etendards.guerre():
            for type_unite in ('zombie', 'Trop_gros_zombie'):
                self.assertFalse(etendards.proteger(g, unite, type_unite, rng))

    def test_palier_persiste_avant_fiche_et_reprise_sans_second_tirage(self):
        g = self.creer(nature='hybride')
        profils = progression.charger()
        profils['j1:general1'].update(niveau=4, progression_combat=1, evolution_apprise=201)
        progression.sauvegarder(profils)
        rng = Mock(randint=lambda a, b: a)
        with patch.object(progression, 'publier_fiche', side_effect=OSError('interruption')):
            with self.assertRaises(OSError):
                progression.valider_evenement(g, 'combat', 'palier', rng)
        avant = progression.charger()['j1:general1']
        self.assertEqual(avant['niveau'], 5)
        self.assertEqual(avant['emplacements_etiquettes_actives'], 2)
        self.assertEqual(avant['points_commandement'], 7)
        with patch.object(rng, 'randint', side_effect=AssertionError('Rejeu')):
            self.assertFalse(progression.valider_evenement(g, 'combat', 'palier', rng))
        self.assertEqual(progression.charger()['j1:general1'], avant)

    def test_anciens_zombies_conservent_capacites_sans_rattrapage(self):
        for nature, places in [('stratege', 3), ('stratege_hybride', 3),
                              ('instinctif', 1), ('instinctif_hybride', 1)]:
            fiche = dict(nature=nature, niveau=25, etat_zombie=True, niveaux_zombie=3,
                         etiquettes={'orc': 3}, moral=50, points_commandement=70)
            apres = progression.migrer_profil(fiche, Mock(randint=Mock(side_effect=AssertionError)))
            self.assertEqual(apres['emplacements_etiquettes_actives'], places)
            self.assertEqual(apres['niveau_etendard'], 0)
            self.assertEqual(apres['migration_orientations'], [])
            self.assertEqual(progression.migrer_profil(apres), apres)

    def test_choc_manoeuvres_et_generaux_successifs_partagent_la_guerre(self):
        g = self.porteur(niveau=2, nombre=3)
        for numero, bloc in ((1, 'avant'), (2, 'arriere')):
            ennemi = self.general('bot', numero=numero, place=str(numero), nombre=1)
            if bloc == 'arriere':
                for unite in (ennemi / 'avant').iterdir():
                    unite.rename(ennemi / 'arriere' / unite.name)
        territoire = g['chemin'].parents[2]
        with etendards.guerre():
            initial = etendards.figer(g)
            with patch.object(self.combats, 'combat_entre_generaux',
                              wraps=self.combats.combat_entre_generaux) as duels:
                self.combats.resoudre_combat_range(territoire, 'OFF/OFF', self.profil)
            self.assertEqual(duels.call_count, 2)
            self.assertIs(etendards.figer(g), initial)
            self.assertTrue(any(n < 2 for n in initial['restantes'].values()))
            self.assertFalse(initial['detruit'])
        self.assertIsNone(etendards._guerre.get())

    def test_capture_migration_privee_publication_et_relecture_sans_retirage(self):
        from support_cycle import GelSimule
        g = self.porteur(niveau=2, nombre=2, nature='hybride')
        profils = progression.charger()
        fiche = profils['j1:general1']
        fiche.update(niveau=20, nature='stratege_hybride')
        fiche.pop('version_progression')
        fichier = self.config.game_path / '.systeme/progression.json'
        fichier.write_text(json.dumps(profils), encoding='utf-8')
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        gestion.preparer()
        prive, homes = gestion.capturer(1)
        self.etat.sauvegarder_cycle_survie(dict(tour=1, phase='resolution'), prive)
        with self.config.racines_generation(prive['game_path'], homes), \
                self.rapports.preparation_privee(gestion.generation / 'rapports'):
            self.rapports.preparer_rapports(prive)
            with patch.object(progression.aleatoire_progression, 'randint', return_value=100) as tirages:
                migree = progression.charger()['j1:general1']
                self.assertEqual(progression.charger()['j1:general1'], migree)
                self.assertLessEqual(tirages.call_count, 4)
                self.assertEqual((migree['emplacements_etiquettes_actives'], migree['niveau_etendard']), (3, 2))
            self.assertEqual(progression.charger()['j1:general1']['version_progression'], 3)
        # La génération privée conserve sa migration même après sortie du contexte.
        contenu = json.loads((prive['game_path'] / '.systeme/progression.json').read_text())
        self.assertEqual(contenu['j1:general1'], migree)
        self.cycle_linux.ecrire_json(gestion.generation / 'resultat.json', {'tour': 1, 'resolution_terminee': True})
        public, stage = gestion.preparer_publication()
        gestion.publier(1, public, stage, False)
        with patch.object(progression.aleatoire_progression, 'randint',
                          side_effect=AssertionError('Migration rejouée après publication')):
            self.assertEqual(progression.charger()['j1:general1'], migree)
            progression.publier_fiche(g['chemin'], migree)
            self.assertEqual(progression.charger()['j1:general1'], migree)

    def test_frontal_et_cascade_surnombre_sans_recharge(self):
        g = self.porteur(niveau=2, nombre=20)
        (g['chemin'] / 'info/ordre_surnombre.txt').write_text('2\n')
        self.profil['configurations_terrain'] = {'est_3': {'attaque_frontale': True}}
        for numero in range(1, 6):
            self.general('bot', numero=numero, nombre=1)
        resoudre = self.combats.resoudre_combat_range
        observations = []

        def observer(*args, **kwargs):
            etendard = etendards.figer(g)
            if observations:
                self.assertIs(etendard, observations[-1][0])
                self.assertEqual(etendard['restantes'], observations[-1][1])
            resultat = resoudre(*args, **kwargs)
            observations.append((etendard, dict(etendard['restantes'])))
            return resultat

        with patch.object(self.combats, 'resoudre_combat_range', side_effect=observer):
            resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil)
        self.assertEqual(resultat['affrontements'], 2)
        self.assertEqual(len(observations), 2)
        self.assertTrue(any(n < 2 for n in observations[0][1].values()))
        self.assertIsNone(etendards._guerre.get())
        with etendards.guerre():
            self.assertEqual(set(etendards.figer(g)['restantes'].values()), {2})

    def test_destruction_general_epuise_etendard_avant_suppression(self):
        g = self.porteur(nombre=1)
        for numero in range(1, 3):
            self.general('bot', numero=numero, nombre=1)
        with patch.object(self.rapports, 'noter_resultat') as rapport:
            self.combats.resoudre_combat_range(self.config.game_path / 'est_3', 'OFF/OFF', self.profil)
        self.assertFalse(g['chemin'].exists())
        destructions = [c for c in rapport.call_args_list if 'détruit : bloc anéanti' in c.args[2]]
        self.assertEqual(len(destructions), 1)
        self.assertIsNone(etendards._guerre.get())

    def test_rapports_distinguent_gains_supplement_basculement_et_protections(self):
        g = self.porteur(nombre=1, nature='hybride')
        profils = progression.charger()
        profils['j1:general1'].update(niveau=14, progression_combat=1,
                                     emplacements_etiquettes_actives=3, evolution_apprise=201)
        progression.sauvegarder(profils)
        self.etat.sauvegarder_cycle_survie({'tour': 1, 'phase': 'resolution'}, self.profil)
        self.rapports.preparer_activites(self.profil, 1)
        sorties = self.racine / 'rapports_prives'
        with self.rapports.preparation_privee(sorties):
            self.rapports.preparer_rapports(self.profil)
            progression.valider_evenement(g, 'combat', 'rapport-palier', Mock(randint=lambda a, b: a))
            with etendards.guerre():
                for _ in range(3):
                    self.combats.supprimer_unites(self.infos(g), 0, g)
        personnel = (self.config.game_path / 'village/j1/hotel_de_ville/rapport_activites.txt').read_text()
        for fragment in ('gains naturels : PC +2, moral +0', 'récompense classique',
                         'récompense supplémentaire', 'étendard royal débloquée',
                         'basculement automatique : stratege → instinctif',
                         'bloc avant : étendard royal', 'détruit : bloc anéanti'):
            self.assertIn(fragment, personnel)
        detail = (sorties / 'archives.log').read_text()
        for fragment in ('infanterie1 sauvé ; 1 charge', 'infanterie1 sauvé ; 0 charge',
                         'détruit : bloc anéanti'):
            self.assertIn(fragment, detail)
        for chemin in (sorties / 'rapport_court.txt',
                       self.config.game_path / 'village/j2/hotel_de_ville/rapport_activites.txt'):
            self.assertNotIn('general1', chemin.read_text())

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
        with (g['chemin'] / 'info/fiche.txt').open('a') as f:
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
        (g['chemin'] / 'info/QG.txt').touch()
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
