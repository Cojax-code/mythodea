"""Règles définies de progression et commandement, sans accès au plateau."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import catalogues
import commandement
import progression


class Progression(unittest.TestCase):
    def fiche(self, nature='stratege', trait='charismatique', **autres):
        return dict(niveau=0, nature=nature, trait_inne=trait, points_commandement=15,
                    moral=0, evolutions_acquises=[], evolution_apprise=None, **autres)

    def test_ids_uniques_et_recettes_inchangees(self):
        catalogues.verifier_catalogues()
        self.assertEqual([catalogues.UNITES[i]['fabrication'] for i in (1, 2, 3)], [5, 5, 5])
        self.assertEqual([catalogues.UNITES[i]['recette'] for i in (1, 2, 3)],
                         [('arc',), ('pique',), ('cheval',)])
        self.assertIsNone(catalogues.UNITES[4]['fabrication'])
        self.assertEqual(len(catalogues.ORDRES), 5)
        self.assertEqual(catalogues.EVOLUTIONS[201]['categorie'], 'commandement')

    def test_nature_et_traits_aux_frontieres_exactes(self):
        for nature, tirage in (('stratege', 45), ('instinctif', 90),
                              ('stratege_hybride', 95), ('instinctif_hybride', 100)):
            for trait, valeur in (('charismatique', 50), ('leader', 51), ('inventeur', 100)):
                rng = Mock()
                rng.randint.side_effect = [tirage, valeur, 1]
                fiche = progression.nouvelles_caracteristiques(rng)
                self.assertEqual((fiche['nature'], fiche['trait_inne'], fiche['niveau']), (nature, trait, 0))
                self.assertEqual(fiche['moral'], 0)
                orientation = nature.removesuffix('_hybride')
                self.assertEqual(fiche['orientation_principale'], orientation)
                self.assertEqual(fiche['points_commandement'], 11 if orientation == 'stratege' else 0)

    def test_distribution_ponderee_exacte(self):
        for nature in progression.RECOMPENSES:
            for trait, poids in progression.RECOMPENSES[nature].items():
                obtenu = dict.fromkeys(poids, 0)
                for valeur in range(1, 101):
                    obtenu[progression.tirer_pondere(poids, Mock(randint=Mock(return_value=valeur)))] += 1
                self.assertEqual(obtenu, poids, (nature, trait))

    def test_commandement_par_tranches(self):
        for niveau, minimum, maximum in ((0, 11, 20), (4, 11, 20), (5, 21, 40),
                                          (9, 21, 40), (10, 31, 60), (14, 31, 60)):
            self.assertEqual(progression.gain_commandement(niveau, Mock(randint=lambda a, b: a)), minimum)
            self.assertEqual(progression.gain_commandement(niveau, Mock(randint=lambda a, b: b)), maximum)

    def test_moral_entier_plafond_et_pas_de_gain_commandement(self):
        fiche = self.fiche('instinctif')
        fiche.update(niveau=9, moral=98, evolution_apprise=202)
        apres, recompense = progression.monter_niveau(fiche, Mock(randint=lambda a, b: b))
        self.assertEqual((apres['niveau'], apres['moral'], recompense), (10, 100, 202))
        self.assertEqual(apres['points_commandement'], fiche['points_commandement'])
        self.assertEqual(fiche['moral'], 98)
        self.assertNotIn(202, progression.evolutions_eligibles(apres))

    def test_recompenses_impossibles_exclues_et_redistribution(self):
        fiche = self.fiche()
        fiche['evolutions_acquises'] = [1002]  # L'ordre disponible est déjà acquis.
        apres, recompense = progression.monter_niveau(fiche, Mock(randint=lambda a, b: b))
        self.assertEqual(recompense, 201)
        self.assertEqual(apres['points_commandement'], 35)
        self.assertEqual(apres['moral'], 0)

    def test_recompense_unite_najoute_pas_commandement(self):
        catalogue = {111: dict(categorie='unite', cible=1, disponible=True, natures=None)}
        fiche = self.fiche()
        apres, recompense = progression.monter_niveau(fiche, catalogue=catalogue)
        self.assertEqual(recompense, 111)
        self.assertEqual(apres['points_commandement'], 15)
        self.assertEqual(apres['evolutions_acquises'], [111])
        self.assertEqual(progression.evolutions_eligibles(apres, catalogue), {})

    def test_memoire_prime_sur_le_tirage_et_est_consommee(self):
        fiche = self.fiche()
        fiche['evolution_apprise'] = 201
        rng = Mock(randint=Mock(return_value=1))
        apres, recompense = progression.monter_niveau(fiche, rng)
        self.assertEqual(recompense, 201)
        self.assertIsNone(apres['evolution_apprise'])
        rng.randint.assert_called_once_with(1, 10)

    def test_memoire_incompatible_ne_perd_aucun_etat(self):
        fiche = self.fiche()
        fiche['evolution_apprise'] = 202
        avant = deepcopy(fiche)
        with self.assertRaises(ValueError):
            progression.monter_niveau(fiche)
        self.assertEqual(fiche, avant)

    def test_aucun_bareme_automatique(self):
        self.assertFalse(progression.progression_due(self.fiche(), {'batailles': 1000}))
        self.assertTrue(progression.progression_due(self.fiche(), {'batailles': 5},
                                                    lambda f, o: o['batailles'] >= 5))


class Commandement(unittest.TestCase):
    def test_effectif_types_generiques_et_diviseur_minimum(self):
        self.assertEqual(commandement.effectif(19, []), 19)
        self.assertEqual(commandement.effectif(19, ['archer', 'archer', 'cavalier']), 9)
        with self.assertRaises(ValueError):
            commandement.effectif(19, ['infanterie'])

    def test_global_entier_sans_arrondi_flottant(self):
        qg = dict(nature='stratege', points_commandement=11)
        autre = dict(nature='stratege', points_commandement=15)
        instinctif = dict(nature='instinctif', points_commandement=0)
        self.assertEqual(commandement.global_armee([qg, autre], qg), 18)
        self.assertEqual(commandement.global_armee([qg, autre, instinctif, instinctif], qg), 9)
        self.assertEqual(commandement.global_armee([], None), 0)
        qg['points_commandement'] = 10**30 + 1
        self.assertEqual(commandement.global_armee([qg, autre], qg), 10**30 + 8)

    def test_qg_egalite_destruction_sans_releve(self):
        a = dict(nature='stratege', points_commandement=20, qg='avant', effectif_bloc_qg=1)
        b = dict(nature='stratege', points_commandement=20, qg='arriere', effectif_bloc_qg=4)
        points = lambda g: g['points_commandement']
        self.assertIsNone(commandement.selectionner_qg([a, b], points))
        b['points_commandement'] = 15
        qg = commandement.QuartierGeneral([a, b], points)
        self.assertIs(qg.actif(lambda g: g['effectif_bloc_qg']), a)
        a['effectif_bloc_qg'] = 0
        self.assertIsNone(qg.actif(lambda g: g['effectif_bloc_qg']))
        a['effectif_bloc_qg'] = 1
        self.assertIsNone(qg.actif(lambda g: g['effectif_bloc_qg']))

    def test_duel_personnel_puis_qg(self):
        a, qg = dict(ordres=[1]), dict(ordres=[2])
        self.assertIs(commandement.donneur_duel(a, qg, lambda g: g['ordres']), a)
        a['ordres'] = []
        self.assertIs(commandement.donneur_duel(a, qg, lambda g: g['ordres']), qg)

    def test_contre_ordres_uniquement_perdant_et_individuel_sans_priorite(self):
        catalogue = {
            1: dict(categorie='globale', disponible=True, contre=False),
            2: dict(categorie='globale', disponible=True, contre=True),
            3: dict(categorie='individuelle', disponible=True, contre=False)}
        for comparaison, attendu in ((1, [1]), (0, []), (-1, [2])):
            self.assertEqual(commandement.ordres_applicables([1, 2], 'stratege', 'globale',
                                                            comparaison, catalogue), attendu)
        self.assertEqual(commandement.ordres_applicables([3], 'instinctif', 'individuelle',
                                                        catalogue=catalogue), [3])
        self.assertEqual(commandement.ordres_applicables([1], 'instinctif', 'globale', 1, catalogue), [])

    def test_confrontation_globale(self):
        a, b = (dict(nature='stratege', points_commandement=p) for p in (20, 19))
        self.assertEqual(commandement.confronter_globaux([a], a, [1002], [b], b, [1002]), ([1002], []))


if __name__ == '__main__':
    unittest.main()
