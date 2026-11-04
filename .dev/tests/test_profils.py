"""Création, compatibilité et École, exclusivement dans un répertoire temporaire."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

import test_mythodea
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import progression
import formation
import catalogues


class ProfilsCibles(unittest.TestCase):
    setUp = test_mythodea.Regressions.setUp
    general = test_mythodea.Regressions.general

    def profil(self, **champs):
        fiche = progression.nouvelles_caracteristiques(Mock(randint=lambda a, b: a))
        fiche.update(champs)
        return fiche

    def installer(self, fiche):
        chemin = self.general()
        general = dict(joueur='j1', nom='general1', chemin=chemin)
        progression.sauvegarder({'j1:general1': fiche})
        progression.publier_fiche(chemin, fiche)
        return general

    def test_creation_champs_actuels_sans_historiques(self):
        chemin = self.general()
        fiche = self.generaux.lire_fiche_general(chemin)
        attendus = {'nom', 'nature', 'orientation_principale', 'trait_inne', 'niveau',
                    'points_commandement', 'moral', 'progression_combat', 'progression_formation',
                    'evolutions_acquises', 'evolution_apprise', 'etiquettes'}
        self.assertEqual(set(fiche), attendus)
        prive = progression.charger()['j1:general1']
        self.assertFalse(progression.CHAMPS_HISTORIQUES.intersection(prive))
        self.assertEqual(prive['etiquettes_apprises_ecole'], [])

    def test_ancienne_fiche_lisible_et_publication_sans_perte(self):
        g = self.installer(self.profil(niveau=10, etiquettes={'infanterie': 3}))
        chemin = g['chemin'] / 'fiche.txt'
        with chemin.open('a', encoding='utf-8') as f:
            f.write('orientation=combattant\nstrategie=7\nforce=8\nexperience=9\n'
                    'etiquettes_permanentes=infanterie\nposition_surnombre=6\n')
        ancienne = self.generaux.lire_fiche_general(g['chemin'])
        self.assertEqual(ancienne['orientation'], 'combattant')
        self.assertEqual(ancienne['nature'], 'stratege')
        progression.publier_fiche(g['chemin'], progression.charger()['j1:general1'])
        relue = self.generaux.lire_fiche_general(g['chemin'])
        self.assertFalse(progression.CHAMPS_HISTORIQUES.intersection(relue))
        self.assertEqual(relue['position_surnombre'], '6')
        self.assertEqual(relue['etiquettes'], "{'infanterie': 3}")

    def test_ancien_profil_rechargement_origines_et_rangs(self):
        fiche = self.profil(niveau=10, etiquettes={'infanterie': 3, 'distance': 2, 'orc': 1},
                           etiquettes_permanentes=['infanterie', 'melee'], force=0,
                           progressions_validees={'combat:ancien': {
                               'niveau': 2, 'recompense': ['etiquette', 'distance']}})
        del fiche['etiquettes_apprises_ecole']
        avant = deepcopy(fiche)
        fichier = self.config.game_path / '.systeme/progression.json'
        fichier.write_text(json.dumps({'j1:general1': fiche}), encoding='utf-8')
        contenu = fichier.read_bytes()
        relu = progression.charger()['j1:general1']
        self.assertEqual(fichier.read_bytes(), contenu)  # Lire ne migre pas sur disque.
        self.assertEqual(relu['etiquettes'], {'infanterie': 3, 'distance': 2, 'orc': 1, 'melee': 1})
        self.assertEqual(relu['etiquettes_apprises_ecole'], ['orc'])
        progression.sauvegarder({'j1:general1': relu})
        self.assertEqual(progression.charger()['j1:general1'], relu)
        self.assertEqual(fiche, avant)
        self.assertNotIn('etiquettes_permanentes', json.loads(fichier.read_text())['j1:general1'])

    def test_toutes_etiquettes_ameliorables_selon_rang_maximal(self):
        for nature in progression.NATURES:
            for niveau in (0, 4, 5, 9, 10, 15):
                for etiquette in catalogues.ETIQUETTES_COMBAT:
                    with self.subTest(nature=nature, niveau=niveau, etiquette=etiquette):
                        fiche = self.profil(nature=nature, niveau=niveau,
                                           etiquettes={etiquette: 1},
                                           etiquettes_permanentes=[etiquette])
                        for rang in range(2, 2 + niveau // 5):
                            fiche = progression.apprendre_etiquette(fiche, etiquette)
                            self.assertEqual(fiche['etiquettes'][etiquette], rang)
                            self.assertEqual(fiche['etiquettes_apprises_ecole'], [])
                        with self.assertRaisesRegex(ValueError, 'maximal'):
                            progression.apprendre_etiquette(fiche, etiquette)

    def test_quota_scolaire_exclut_creation_paliers_et_roulette(self):
        fiche = self.profil(niveau=4)
        for _ in range(2):  # Palier N5 puis roulette N6, en plus de la création.
            fiche, _ = progression.monter_niveau(fiche, Mock(randint=lambda a, b: b))
        self.assertEqual(len(fiche['etiquettes']), 3)
        self.assertEqual(fiche['etiquettes_apprises_ecole'], [])
        inconnues = [n for n in catalogues.ETIQUETTES_COMBAT if n not in fiche['etiquettes']]
        for nom in inconnues[:2]:
            fiche = progression.apprendre_etiquette(fiche, nom)
        self.assertEqual(fiche['etiquettes_apprises_ecole'], inconnues[:2])
        with self.assertRaisesRegex(ValueError, 'emplacement'):
            progression.apprendre_etiquette(fiche, inconnues[2])
        nom = next(iter(fiche['etiquettes']))
        self.assertEqual(progression.apprendre_etiquette(fiche, nom)['etiquettes'][nom], 2)

    def test_ecole_ecriture_lecture_ancienne_etiquette_et_rejeu(self):
        g = self.installer(self.profil(niveau=5, etiquettes={'infanterie': 1},
                                      etiquettes_permanentes=['infanterie']))
        for tour, demande in ((1, {'ecrire': 'e 001 2001'}), (2, {'lire': 'a 001 2001'})):
            self.assertTrue(formation.commencer_sejour(
                tour, g, 'ecole_officiers', 'allies', [1, 2, 3], **demande))
            self.assertFalse(formation.valider_sejour(tour, g, 'ecole_officiers', 'allies', [1, 2, 3]))
            self.assertTrue(formation.valider_sejour(tour, g, 'ecole_officiers', 'allies', [1, 2, 3], True))
            self.assertFalse(formation.valider_sejour(tour, g, 'ecole_officiers', 'allies', [1, 2, 3], True))
        relu = progression.charger()['j1:general1']
        self.assertEqual(relu['etiquettes'], {'infanterie': 2})
        self.assertEqual(relu['etiquettes_apprises_ecole'], [])
        self.assertEqual(self.generaux.lire_fiche_general(g['chemin'])['etiquettes'], "{'infanterie': 2}")

    def test_combat_et_formation_jauges_independantes_et_persistance(self):
        g = self.installer(self.profil(evolution_apprise=201))
        for voie, total in (('combat', 2), ('formation', 3)):
            for numero in range(total):
                self.assertTrue(progression.valider_evenement(g, voie, str(numero), Mock(randint=lambda a, b: a)))
                self.assertFalse(progression.valider_evenement(g, voie, str(numero)))
        fiche = progression.charger()['j1:general1']
        self.assertEqual((fiche['niveau'], fiche['progression_combat'], fiche['progression_formation']), (2, 0, 0))
        self.assertEqual(len(fiche['progressions_validees']), 5)
        self.assertEqual(self.generaux.lire_fiche_general(g['chemin'])['niveau'], '2')

    def test_zombie_acquisition_amelioration_et_selection_speciale(self):
        fiche = self.profil(nature='instinctif', niveau=4, etat_zombie=True,
                           etiquettes={'infanterie': 1}, moral=33)
        apres, gain = progression.monter_niveau(fiche, Mock(randint=lambda a, b: a))
        self.assertEqual(gain, ('etiquette_zombie', 'mort_vivant'))
        self.assertEqual(progression.capacite_maximale(apres), 22)
        self.assertEqual((apres['moral'], apres['points_commandement']), (33, fiche['points_commandement']))
        apres = progression.apprendre_etiquette(apres, 'mort_vivant')
        self.assertEqual(apres['etiquettes']['mort_vivant'], 2)
        self.assertEqual(apres['etiquettes_apprises_ecole'], [])
        g = self.installer(apres)
        self.assertEqual(progression.caracteristiques_general(g)['etiquettes_actives'], ['infanterie', 'mort_vivant'])
        rng = Mock(randint=Mock(side_effect=AssertionError('Nouveau tirage interdit')))
        suivant, gain = progression.monter_niveau(progression.charger()['j1:general1'], rng)
        self.assertIsNone(gain)
        self.assertEqual(suivant['etiquettes']['mort_vivant'], 2)
