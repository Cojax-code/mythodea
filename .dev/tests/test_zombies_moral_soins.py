"""Exclusions zombies explicites, sans modifier les anciennes fiches."""
import unittest
from unittest.mock import patch
import test_unites_v2


class ZombiesMoralSoins(unittest.TestCase):
    setUp = test_unites_v2.UnitesV2.setUp
    activer = test_unites_v2.UnitesV2.activer
    general = test_unites_v2.UnitesV2.general
    creer = test_unites_v2.UnitesV2.creer
    infos = test_unites_v2.UnitesV2.infos
    modules = test_unites_v2.UnitesV2.modules
    speciale = test_unites_v2.UnitesV2.speciale

    def test_general_zombie_ne_sauve_pas_meme_avec_ancien_moral(self):
        g = self.creer(nombre=2)
        fiches = self.progression.charger()
        fiches['j1:general1'].update(etat_zombie=True, moral=100)
        self.progression.sauvegarder(fiches)
        derived = self.unites.caracteristiques_armee(fiches['j1:general1'],
            {'avant': {'orc_assaillant': 20, 'chevalier_clinquant': 2}})
        self.assertEqual(derived['moral'], 0)
        self.assertEqual(derived['points_commandement'], fiches['j1:general1']['points_commandement'])
        self.assertEqual(len(self.combats.supprimer_unites(self.infos(g), 0, g)), 2)
        self.assertEqual(self.progression.charger()['j1:general1']['moral'], 100)

    def test_soldat_zombie_jamais_sauve_meme_catalogue_ancien(self):
        g = self.creer(nombre=0)
        path, identifiant = self.speciale(g, 'zombie')
        with patch.dict(self.unites.definition('zombie'), blessures=3):
            self.assertEqual(self.unites.blessures_max('zombie', 10), 0)
            self.assertEqual(len(self.soldats.pertes(self.infos(g), 0, 100)), 1)
        self.assertFalse(path.exists())
        self.assertEqual(self.soldats.charger()[identifiant]['blessures'], 0)

    def test_hopital_ne_restaure_pas_les_blessures_zombies(self):
        g = self.creer(nombre=0)
        for index, unit in enumerate(('zombie', 'Trop_gros_zombie'), 1):
            _, identifiant = self.speciale(g, unit)
            registry = self.soldats.charger()
            registry[identifiant]['blessures'] = 2
            self.soldats.sauvegarder(registry)
            presence = {identifiant: [1, 2, 3]}
            with patch.dict(self.unites.definition(unit), soins='hopital', tours_soins=1):
                self.formation.commencer_sejour(index, g, 'hopital', 'allies', [7], unites=presence)
                self.assertTrue(self.formation.valider_sejour(index, g, 'hopital', 'allies', [7], True, presence))
            self.assertEqual(self.soldats.charger()[identifiant]['blessures'], 2)

    def test_chaman_soigne_les_vivants_uniquement(self):
        g = self.creer(nombre=0, territoire='est_1')
        self.speciale(g, 'orc_chaman')
        _, vivant = self.speciale(g, 'orc_archer', bloc='arriere')
        _, zombie = self.speciale(g, 'zombie', bloc='droite')
        _, gros = self.speciale(g, 'Trop_gros_zombie', bloc='gauche')
        registry = self.soldats.charger()
        for identifiant in (vivant, zombie, gros):
            registry[identifiant]['blessures'] = 2
        self.soldats.sauvegarder(registry)
        with patch.dict(self.unites.definition('zombie'), soins='chaman'), \
                patch.dict(self.unites.definition('Trop_gros_zombie'), soins='chaman'):
            self.unites.soigner_victoire_territoriale(self.profil, g['chemin'].parents[2], 'victoire')
        registry = self.soldats.charger()
        self.assertEqual(registry[vivant]['blessures'], 0)
        self.assertEqual(registry[zombie]['blessures'], 2)
        self.assertEqual(registry[gros]['blessures'], 2)
