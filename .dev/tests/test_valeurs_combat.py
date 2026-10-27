"""Valeurs individuelles et équivalence à l'ancien combat, en isolation."""
from itertools import product
from fractions import Fraction
import random
import unittest
from unittest.mock import patch

import test_soldats_formation


class ValeursCombat(unittest.TestCase):
    activer = test_soldats_formation.SoldatsFormation.activer
    general = test_soldats_formation.SoldatsFormation.general
    creer = test_soldats_formation.SoldatsFormation.creer
    infos = test_soldats_formation.SoldatsFormation.infos
    modules = test_soldats_formation.SoldatsFormation.modules

    def setUp(self):
        test_soldats_formation.SoldatsFormation.setUp(self)
        self.modules()
        self.catalogues = self.combats.catalogues

    @staticmethod
    def bloc(type_unite, nombre):
        return dict(type=type_unite, nombre=nombre)

    def test_catalogue_valeurs_separees_de_fabrication_et_validation_stricte(self):
        self.assertEqual([self.catalogues.UNITES[i]['valeur_combat'] for i in (1, 2, 3, 4)], [5] * 4)
        self.assertIsNone(self.catalogues.UNITES[4]['fabrication'])
        definition = self.catalogues.UNITES[1]
        for valeur in (0, -1, True, False, 5.0, '5', None):
            with self.subTest(valeur=valeur), patch.dict(definition, valeur_combat=valeur):
                with self.assertRaisesRegex(ValueError, 'entier strictement positif'):
                    self.catalogues.verifier_catalogues()
                with self.assertRaises(ValueError):
                    self.combats.valeur_base_bloc(self.bloc('archer', 10))
        for valeur in (3, 5, 7, 10**30):
            with patch.dict(definition, valeur_combat=valeur):
                self.catalogues.verifier_catalogues()
                self.assertEqual(self.combats.valeur_base_bloc(self.bloc('archer', 10)), valeur)
        with patch.dict(definition, fabrication=999):
            self.assertEqual(self.catalogues.valeur_combat('archer'), 5)

    def test_puissance_effectif_reel_quatre_blocs(self):
        for bloc in self.config.ordre_blocs:
            for nombre, puissance in ((0, 0), (10, 50), (20, 100)):
                infos = self.bloc('archer', nombre)
                self.assertEqual(nombre * self.combats.valeur_base_bloc(infos, bloc), puissance)
        with patch.dict(self.catalogues.UNITES[1], valeur_combat=7):
            self.assertEqual(10 * self.combats.valeur_base_bloc(self.bloc('archer', 10)), 70)

    def test_memes_unites_pertes_simultanees_et_effectifs_differents(self):
        for n1, n2, attendu in ((10, 10, (0, 0)), (20, 10, (10, 0)), (3, 8, (0, 5))):
            self.assertEqual(self.combats.combat_bloc(self.bloc('archer', n1), self.bloc('archer', n2)), attendu)

    def test_valeurs_3_5_et_5_7_sans_avantage(self):
        # Les valeurs futures sont simulées dans les types existants, sans en créer.
        for a, b, attendu in ((3, 5, (0, 4)), (5, 7, (0, 3))):
            with patch.dict(self.catalogues.UNITES[1], valeur_combat=a), \
                    patch.dict(self.catalogues.UNITES[2], valeur_combat=b), \
                    patch.object(self.combats, 'multiplicateur', return_value=1):
                x, y = self.bloc('archer', 10), self.bloc('piquier', 10)
                self.assertEqual(self.combats.combat_bloc(x, y), attendu)
                self.assertEqual(self.combats.combat_bloc(y, x), attendu[::-1])

    def test_avantages_naturels_appliques_une_seule_fois(self):
        avantages = (('archer', 'piquier'), ('piquier', 'cavalier'), ('cavalier', 'archer'),
                     ('cavalerie_lourde', 'archer'), ('cavalerie_lourde', 'cavalier'),
                     ('piquier', 'cavalerie_lourde'))
        for fort, faible in avantages:
            self.assertEqual(self.combats.combat_bloc(self.bloc(fort, 10), self.bloc(faible, 10)), (5, 0))
        with patch.dict(self.catalogues.UNITES[1], valeur_combat=3):
            # 10 archers : valeur effective 6 ; 10 piquiers : valeur 5.
            self.assertEqual(self.combats.combat_bloc(self.bloc('archer', 10), self.bloc('piquier', 10)), (2, 0))

    def test_fatigue_meme_type_sans_annuler_avantage_naturel(self):
        a, b = self.bloc('archer', 10), self.bloc('archer', 10)
        self.assertEqual(self.combats.combat_bloc(a, b, True, False), (0, 5))
        self.assertEqual(self.combats.combat_bloc(a, b, False, True), (5, 0))
        self.assertEqual(self.combats.combat_bloc(a, b, True, True), (0, 0))
        self.assertEqual(self.combats.combat_bloc(a, self.bloc('piquier', 10), True, False), (5, 0))

    def test_lourde_seuil_recalcule_apres_pertes(self):
        lourd, adverse = self.bloc('cavalerie_lourde', 15), self.bloc('archer', 20)
        resultat = self.combats.combat_bloc(lourd, adverse, bloc_1='avant')
        self.assertEqual(resultat, (10, 0))
        lourd['nombre'] = resultat[0]
        self.assertEqual(self.combats.valeur_base_bloc(lourd, 'avant'), 5)
        self.assertEqual(self.combats.combat_bloc(lourd, adverse, bloc_1='avant'), (0, 0))
        for bloc in ('droite', 'gauche', 'arriere'):
            self.assertEqual(self.combats.combat_bloc(self.bloc('cavalerie_lourde', 15), adverse,
                                                    bloc_1=bloc), (5, 0))

    def test_fatigue_individuelle_exemples_officiels_et_priorites(self):
        # Effectifs, fatigués, bonus équivalents, puissances, résistances, survivants.
        cas = (
            (6, 0, 3, 3, (6, 0), (60, 15), (10, 5), (5, 0)),
            (8, 0, 4, 1, (2, 0), (50, 20), (Fraction(25, 4), 5), (5, 0)),
            (5, 0, 5, 1, (1, 0), (30, 25), (6, 5), (1, 0)),
            # Fatigués/fatigués d'abord : un seul frais avantagé dans D1.
            (5, 2, 5, 3, (1, 0), (30, 25), (6, 5), (1, 0)),
            (5, 2, 5, 2, (0, 0), (25, 25), (5, 5), (0, 0)),
            (8, 2, 4, 1, (1, 1), (45, 25), (Fraction(45, 8), Fraction(25, 4)), (4, 0)),
            (7, 2, 3, 1, (Fraction(4, 3), 1), (Fraction(125, 3), 20),
             (Fraction(125, 21), Fraction(20, 3)), (4, 0)),
            # Le surnombre fatigué contribue mais ne reçoit aucun bonus.
            (8, 8, 3, 1, (0, 2), (40, 25), (5, Fraction(25, 3)), (3, 0)),
        )
        for n1, t1, n2, t2, bonus, puissances, resistances, attendu in cas:
            with self.subTest(effectifs=(n1, n2), fatigues=(t1, t2)):
                f1, f2 = (False,) * (n1-t1) + (True,) * t1, (False,) * (n2-t2) + (True,) * t2
                self.assertEqual(self.combats.bonus_fatigue(n1, f1, n2, f2), bonus)
                self.assertEqual(tuple(5 * (n+b) for n, b in zip((n1, n2), bonus)), puissances)
                self.assertEqual(tuple(Fraction(p, n) for p, n in zip(puissances, (n1, n2))), resistances)
                a, b = self.bloc('piquier', n1), self.bloc('piquier', n2)
                self.assertEqual(self.combats.combat_bloc(a, b, f1, f2), attendu)
                self.assertEqual(self.combats.combat_bloc(b, a, f2, f1), attendu[::-1])
                self.assertTrue(all(type(n) is int for n in self.combats.combat_bloc(a, b, f1, f2)))

    def test_fatigue_individuelle_invariante_aux_permutations_sans_hasard(self):
        a, b = self.bloc('piquier', 7), self.bloc('piquier', 3)
        hasard = random.getstate()
        for f1 in ((False,) * 5 + (True,) * 2, (True, False, False, True, False, False, False)):
            for f2 in ((True, False, False), (False, False, True)):
                self.assertEqual(self.combats.combat_bloc(a, b, f1, f2), (4, 0))
        self.assertEqual(random.getstate(), hasard)

    def test_fatigue_individuelle_conserve_types_herisson_et_seuil_lourd(self):
        melange = (False,) * 3 + (True,) * 2
        for fort, faible in (('archer', 'piquier'), ('piquier', 'cavalier'),
                            ('cavalier', 'archer'), ('cavalerie_lourde', 'cavalier')):
            self.assertEqual(self.combats.combat_bloc(self.bloc(fort, 5), self.bloc(faible, 5),
                                                    melange, melange), (3, 0))
        commandant = object()
        with patch.object(self.combats.ordres_pipeline, 'effet',
                          side_effect=lambda g, effet: g is commandant and effet == 'herisson'):
            self.assertEqual(self.combats.combat_bloc(self.bloc('piquier', 5), self.bloc('cavalier', 5),
                melange, melange, general_1=commandant), (4, 0))
        # Même type lourd : formation ×2 puis fatigue individuelle (un frais avantagé).
        lourd, adverse = self.bloc('cavalerie_lourde', 15), self.bloc('cavalerie_lourde', 15)
        f1, f2 = (False,) * 14 + (True,), (False,) * 13 + (True,) * 2
        self.assertEqual(self.combats.combat_bloc(lourd, adverse, f1, f2, 'avant', 'droite'), (8, 0))
        # Le même bloc sous le seuil perd le facteur de formation.
        lourd['nombre'] = 14
        # Un frais adverse reste libre : bonus 1/14, résistance 211/42.
        # floor(75 / (211/42)) = 14 pertes adverses, donc un survivant.
        self.assertEqual(self.combats.combat_bloc(lourd, adverse, f1[1:], f2, 'avant', 'droite'), (0, 1))

    def test_fatigue_individuelle_valide_effectifs_et_booleens(self):
        a = self.bloc('archer', 3)
        for fatigue in ((False,), (0, 0, 1), 'non', 2, None):
            with self.subTest(fatigue=fatigue), self.assertRaises(ValueError):
                self.combats.combat_bloc(a, a, fatigue, False)
        self.assertEqual(self.combats.combat_bloc(self.bloc('vide', 0), a, (), (False,) * 3), (0, 3))

    def test_fatigue_individuelle_homogene_equivalente_aux_booleens(self):
        # Toutes les tailles classiques et surnombre ; tous les types, positions,
        # fatigues homogènes sont déjà contrôlés contre l'oracle historique plus bas.
        for n1, n2, f1, f2 in product((*range(21), 25), (*range(21), 25), (False, True), (False, True)):
            a, b = self.bloc('piquier', n1), self.bloc('piquier', n2)
            self.assertEqual(self.combats.combat_bloc(a, b, (f1,) * n1, (f2,) * n2),
                             self.combats.combat_bloc(a, b, f1, f2))

    def test_blocs_vides_aucun_degats_ni_division(self):
        vide = self.bloc('vide', 0)
        self.assertEqual(self.combats.valeur_base_bloc(vide), 0)
        self.assertEqual(self.combats.combat_bloc(vide, vide), (0, 0))
        for definition in self.catalogues.UNITES.values():
            plein = self.bloc(definition['nom'], 20)
            self.assertEqual(self.combats.combat_bloc(vide, plein, bloc_2='avant'), (0, 20))
            self.assertEqual(self.combats.combat_bloc(plein, vide, bloc_1='avant'), (20, 0))

    def test_equivalence_historique_tous_types_fatigues_positions_et_effectifs(self):
        # Oracle figé de l'ancienne échelle 1, indépendant du catalogue et des
        # fonctions actuelles de bonus. 774 400 confrontations comparées.
        types = ('archer', 'piquier', 'cavalier', 'cavalerie_lourde')
        avantages = {('archer', 'piquier'), ('piquier', 'cavalier'), ('cavalier', 'archer'),
                     ('cavalerie_lourde', 'archer'), ('cavalerie_lourde', 'cavalier'),
                     ('piquier', 'cavalerie_lourde')}
        nombres = (*range(21), 25)
        blocs = (None, 'avant', 'droite', 'gauche', 'arriere')
        for t1, t2, n1, n2, f1, f2, b1, b2 in product(types, types, nombres, nombres,
                                                     (False, True), (False, True), blocs, blocs):
            v1 = 2 if t1 == 'cavalerie_lourde' and b1 == 'avant' and n1 >= 15 else 1
            v2 = 2 if t2 == 'cavalerie_lourde' and b2 == 'avant' and n2 >= 15 else 1
            v1 *= 2 if (t1, t2) in avantages or (t1 == t2 and f2 and not f1) else 1
            v2 *= 2 if (t2, t1) in avantages or (t1 == t2 and f1 and not f2) else 1
            attendu = (max(0, n1 - n2 * v2 // v1), max(0, n2 - n1 * v1 // v2))
            resultat = self.combats.combat_bloc(self.bloc(t1, n1), self.bloc(t2, n2), f1, f2, b1, b2)
            if resultat != attendu:
                self.fail(f'{(t1, t2, n1, n2, f1, f2, b1, b2)} : {resultat} != {attendu}')

    def test_valeurs_differentes_moral_blessures_et_identites_sur_disque(self):
        general = self.creer(nombre=10, nature='instinctif')
        adverse = self.general(joueur='bot', nombre=10, equipement='pique')
        ennemi = dict(joueur='bot', nom=adverse.name, chemin=adverse)
        unites = self.infos(general)['unites']
        self.soldats.terminer_bataille(unites, 'avant')
        identites = {self.soldats.marqueur(u) for u in unites}
        with patch.dict(self.catalogues.UNITES[1], valeur_combat=3), \
                patch.object(self.combats, 'multiplicateur', return_value=1):
            armee = {g['joueur']: self.generaux.lire_blocs_general(g['chemin']) for g in (general, ennemi)}
            detail = self.combats.confrontation_directe(armee, general, ennemi, 'avant')
            # Les 10 pertes alliées sont sauvées, les 6 pertes adverses supprimées.
            self.assertEqual((detail['final_1'], detail['final_2']), (10, 4))
            registre = self.soldats.charger()
            self.assertTrue(all((registre[i]['blessures'], registre[i]['batailles']) == (1, 1)
                                for i in identites))
            self.assertEqual({self.soldats.marqueur(u) for u in self.infos(general)['unites']}, identites)
            self.assertEqual(self.generaux.total_general_depuis_chemin(adverse), 4)
            # Nouvelle confrontation : les blessés à leur limite ne sont plus sauvés.
            armee = {g['joueur']: self.generaux.lire_blocs_general(g['chemin']) for g in (general, ennemi)}
            detail = self.combats.confrontation_directe(armee, general, ennemi, 'avant')
            self.assertEqual((detail['final_1'], detail['final_2']), (4, 0))
            self.assertEqual(sum(self.soldats.charger()[i].get('detruit', False) for i in identites), 6)


if __name__ == '__main__':
    unittest.main()
