"""Formules V2 confirmées, sans exécution d'effets en partie."""
import sys
import unittest
import random
from unittest.mock import Mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import ordres_calculs_v2 as calculs


class TestOrdresCalculsV2(unittest.TestCase):
    def test_prevision_muraille_fatigue_individuelle(self):
        from unittest.mock import patch
        import combats
        general, adverse = object(), object()
        avant = {'type': 'archer', 'nombre': 3}
        oppose = {'type': 'archer', 'nombre': 2}
        fatigue = (True, False, True)
        fatigue_adverse = (False, True)
        with patch.object(combats.progression, 'general_recoit_ordre', return_value=True), patch.object(
                combats.ordres_pipeline, 'identite', return_value=('j1', 'general1')), patch.object(
                combats, 'combat_bloc', return_value=(2, 1)) as calcul:
            resultat = combats.previsions_avant_muraille(
                [(general, avant, fatigue)], oppose, bloc_adverse='avant',
                general_adverse=adverse, fatigue_adverse=fatigue_adverse)
        self.assertEqual(resultat[0]['survivants'], (2, 1))
        self.assertEqual(calcul.call_args.args[2:4], (fatigue, fatigue_adverse))

    def test_prevision_muraille_refuse_fatigue_invalide(self):
        from unittest.mock import patch
        import combats
        general, adverse = object(), object()
        avant = {'type': 'archer', 'nombre': 3}
        oppose = {'type': 'archer', 'nombre': 2}
        with patch.object(combats.progression, 'general_recoit_ordre', return_value=True), patch.object(
                combats.ordres_pipeline, 'identite', return_value=('j1', 'general1')):
            with self.assertRaisesRegex(ValueError, 'Fatigue'):
                combats.previsions_avant_muraille(
                    [(general, avant, (True, False))], oppose,
                    bloc_adverse='avant', general_adverse=adverse)
            with self.assertRaisesRegex(ValueError, 'Fatigue'):
                combats.previsions_avant_muraille(
                    [(general, avant, False)], oppose,
                    bloc_adverse='avant', general_adverse=adverse,
                    fatigue_adverse=(True,))

    def test_muraille_transmet_les_priorites_au_moteur_reel(self):
        from unittest.mock import patch
        import combats
        infos_1 = {'nombre': 2, 'unites': ['a', 'b']}
        infos_2 = {'nombre': 1, 'unites': ['c']}
        g1, g2 = {'joueur': 'j1'}, {'joueur': 'j2'}
        with patch.object(combats, 'combat_bloc', return_value=(1, 0)), patch.object(
                combats, 'supprimer_unites', side_effect=[['a'], ['c']]) as pertes, patch.object(
                combats.unites, 'apres_confrontation'), patch.object(
                combats.soldats, 'affrontement'):
            combats.resoudre_blocs(
                infos_1, infos_2, g1, g2, 'avant', 'avant', False, False,
                prioritaires_1=('a',))
        self.assertEqual(pertes.call_args_list[0].kwargs['unites_prioritaires'], ('a',))
        self.assertEqual(pertes.call_args_list[1].kwargs['unites_prioritaires'], ())

    def test_muraille_applique_victimes_sans_second_tirage(self):
        import soldats
        from unittest.mock import patch
        blocs = {
            'g1': {'unites': ['a', 'b'], 'nombre': 2},
            'g2': {'unites': ['c', 'd'], 'nombre': 2},
        }
        victimes = {'g1': ['a'], 'g2': ['d']}
        moraux = {'g1': 20, 'g2': 40}
        with patch.object(soldats, 'pertes', return_value=[]) as appliquer:
            resultats = soldats.appliquer_victimes_muraille(
                blocs, victimes, moraux, random.Random(3))
        self.assertEqual(resultats, {'g1': [], 'g2': []})
        self.assertEqual(appliquer.call_count, 2)
        self.assertEqual(appliquer.call_args_list[0].kwargs['victimes_choisies'], ['a'])
        self.assertEqual(appliquer.call_args_list[1].kwargs['victimes_choisies'], ['d'])
        self.assertEqual(appliquer.call_args_list[0].args[2], 20)
        self.assertEqual(appliquer.call_args_list[1].args[2], 40)

    def test_muraille_victimes_collectives_gardent_leur_general(self):
        import soldats
        from collections import Counter
        blocs = {
            'g1': {'unites': ('g1_a', 'g1_b')},
            'g2': {'unites': ('g2_a', 'g2_b')},
        }
        repartition = soldats.repartir_victimes_muraille(
            blocs, 3, 'g1', random.Random(42))
        self.assertEqual(sum(map(len, repartition.values())), 3)
        self.assertTrue(set(repartition['g1']).issubset(set(blocs['g1']['unites'])))
        self.assertTrue(set(repartition['g2']).issubset(set(blocs['g2']['unites'])))
        comptes = Counter()
        for graine in range(2400):
            victime = soldats.repartir_victimes_muraille(
                blocs, 1, 'g1', random.Random(graine))
            comptes['g1'] += len(victime['g1'])
            comptes['g2'] += len(victime['g2'])
        self.assertGreater(comptes['g1'], comptes['g2'] * 1.7)
        self.assertLess(comptes['g1'], comptes['g2'] * 2.3)
        self.assertEqual(
            soldats.repartir_victimes_muraille(blocs, 0, 'g1', random.Random(1)),
            {'g1': [], 'g2': []})

    def test_muraille_interdit_soldats_partages_et_pertes_excessives(self):
        import soldats
        blocs = {'a': {'unites': ['x']}, 'b': {'unites': ['x']}}
        with self.assertRaises(ValueError):
            soldats.repartir_victimes_muraille(blocs, 1, 'a', random.Random(1))
        with self.assertRaises(ValueError):
            soldats.repartir_victimes_muraille(
                {'a': {'unites': ['x']}}, 2, 'a', random.Random(1))

    def test_muraille_pondere_x2_le_general_engage_sans_remise(self):
        import soldats
        from collections import Counter
        infos = {'unites': ['engage', 'allie'], 'nombre': 2}
        tirages = Counter()
        for graine in range(4000):
            victimes, sauvetages = soldats.selectionner_victimes(
                infos, 1, 0, random.Random(graine),
                unites_prioritaires=('engage',))
            tirages[victimes[0]] += 1
            self.assertFalse(sauvetages)
        self.assertGreater(tirages['engage'], tirages['allie'] * 1.7)
        self.assertLess(tirages['engage'], tirages['allie'] * 2.3)
        victimes, _ = soldats.selectionner_victimes(
            infos, 0, 0, random.Random(12),
            unites_prioritaires=('engage',))
        self.assertEqual(set(victimes), set(infos['unites']))
        self.assertEqual(len(victimes), 2)

    def test_muraille_uniforme_par_defaut_inchange(self):
        import soldats
        infos = {'unites': ['engage', 'allie', 'autre'], 'nombre': 3}
        graine = 73
        victimes, _ = soldats.selectionner_victimes(
            infos, 2, 0, random.Random(graine))
        self.assertEqual(victimes, random.Random(graine).sample(infos['unites'], 1))

    def test_muraille_choc_reutilise_resolution_reelle(self):
        from unittest.mock import patch
        import combats
        a = {'joueur': 'j1', 'camp': 'a'}
        b = {'joueur': 'j2', 'camp': 'b'}
        vue = Mock()
        vue.blocs.side_effect = lambda g: {'avant': {'nombre': 3 if g is a else 2}}
        with patch.object(combats.bouclier_vivant, 'presence_bouclier',
                          return_value=False), patch.object(
                combats, 'confrontation_directe',
                return_value={'moment': 'Choc', 'final_1': 2, 'final_2': 1}) as reel:
            resultat = combats.engager_avant_muraille(a, b, participants=vue)
        self.assertEqual(resultat['final_1'], 2)
        self.assertEqual(reel.call_args.args[1:], (a, b, 'avant'))
        self.assertIs(reel.call_args.kwargs['participants'], vue)
        vue.verifier_duel.assert_called_once_with(a, b)

    def test_muraille_refuse_bouclier_non_raccorde(self):
        from unittest.mock import patch
        import combats
        a = {'joueur': 'j1', 'camp': 'a'}
        b = {'joueur': 'j2', 'camp': 'b'}
        with patch.object(combats.bouclier_vivant, 'presence_bouclier',
                          return_value=True), patch.object(
                combats, 'confrontation_directe') as reel:
            with self.assertRaisesRegex(NotImplementedError, 'Bouclier'):
                combats.engager_avant_muraille(a, b, participants=Mock())
            reel.assert_not_called()

    def test_duel_transmet_exclusion_avant_sans_changer_defaut(self):
        from unittest.mock import patch
        import combats
        a = {'joueur': 'j1', 'camp': 'a', 'nom': 'general1'}
        b = {'joueur': 'j2', 'camp': 'b', 'nom': 'general2'}
        vue = Mock()
        vue.total.return_value = 3
        vue.present.return_value = True
        vue.supprimer_general_si_vide.return_value = False
        class Contexte:
            def __init__(self, valeur):
                self.valeur = valeur
            def __enter__(self):
                return self.valeur
            def __exit__(self, *_):
                return False
        with patch.object(combats.ordres_pipeline, 'duel', return_value=Contexte([])), patch.object(
                combats.ordres_pipeline, 'participations_duel',
                return_value=Contexte(vue)), patch.object(
                combats.unites, 'duel', return_value=Contexte(None)), patch.object(
                combats.ordres_pipeline, 'rafales', return_value=[]), patch.object(
                combats, '_combat_entre_generaux', return_value={'chocs': [], 'manoeuvres': []}) as calcul:
            combats.combat_entre_generaux(a, b, participants=vue,
                                         avant_exclus_manoeuvre=True)
            self.assertTrue(calcul.call_args.kwargs['avant_exclus_manoeuvre'])
            combats.combat_entre_generaux(a, b, participants=vue)
            self.assertFalse(calcul.call_args.kwargs['avant_exclus_manoeuvre'])

    def test_muraille_manoeuvre_masque_avant_sans_perte(self):
        import combats
        unites_avant = [object(), object()]
        original = {
            'j1': {
                'avant': {'nombre': 2, 'unites': unites_avant, 'type': 'archer'},
                'arriere': {'nombre': 3, 'unites': [object()], 'type': 'piquier'},
            },
            'j2': {
                'avant': {'nombre': 1, 'unites': [object()], 'type': 'cavalier'},
                'arriere': {'nombre': 1, 'unites': [object()], 'type': 'archer'},
            },
        }
        vue = combats.retirer_avants_de_manoeuvre(original)
        for camp in ('j1', 'j2'):
            self.assertEqual(vue[camp]['avant']['nombre'], 0)
            self.assertEqual(vue[camp]['avant']['unites'], [])
            self.assertIs(vue[camp]['arriere'], original[camp]['arriere'])
        self.assertEqual(original['j1']['avant']['nombre'], 2)
        self.assertIs(original['j1']['avant']['unites'], unites_avant)

    def test_muraille_preparation_territoriale_reutilise_pipeline(self):
        from unittest.mock import patch
        import combats
        g = {'joueur': 'j1', 'nom': 'general1'}
        forces = {'camp1': {'1': g}}
        formations = {'camp1': {'ordres': {'muraille_humaine'}, 'qg': ('j1', 'general1')}}
        attendu = {'choisi': ('j1', 'general1'), 'previsions': ('prevision',)}
        with patch.object(combats.ordres_pipeline, 'participants_muraille_territoire',
                          return_value=(g,)) as filtrer, patch.object(
                combats, 'prochain_avant_muraille', return_value=attendu) as choisir:
            decision = combats.preparer_muraille_territoire(
                forces, formations, 'camp1', object(), aleatoire=random.Random(2))
        self.assertEqual(decision['choisi'], ('j1', 'general1'))
        self.assertEqual(decision['participants'], (g,))
        filtrer.assert_called_once()
        choisir.assert_called_once()

    def test_muraille_preparation_territoriale_sans_participants(self):
        from unittest.mock import patch
        import combats
        with patch.object(combats.ordres_pipeline, 'participants_muraille_territoire',
                          return_value=()), patch.object(
                combats, 'prochain_avant_muraille') as choisir:
            resultat = combats.preparer_muraille_territoire(
                {}, {}, 'camp1', object(), aleatoire=random.Random(1))
        self.assertIsNone(resultat['choisi'])
        choisir.assert_not_called()

    def test_muraille_pilote_utilise_choc_reel_par_defaut(self):
        from unittest.mock import patch
        import combats
        general = {'id': 1}
        with patch.object(combats.ordres_pipeline, 'identite',
                          return_value=('j1', 'g1')), patch.object(
                combats, 'prochain_avant_muraille',
                side_effect=[{'choisi': ('j1', 'g1')}, {'choisi': None}]), patch.object(
                combats, 'engager_avant_muraille', return_value={'moment': 'Choc'}) as choc:
            resultats = combats.enchainer_avants_muraille(
                [general], object(), aleatoire=random.Random(1))
        self.assertEqual(resultats, ((('j1', 'g1'), {'moment': 'Choc'}),))
        choc.assert_called_once()

    def test_muraille_utilise_qg_territorial_pour_les_designations(self):
        from unittest.mock import patch
        import combats
        general = {'id': 1}
        with patch.object(combats.ordres_pipeline, 'identite',
                          return_value=('j1', 'g1')), patch.object(
                combats.ordres_pipeline, 'transmission_muraille_active',
                return_value=False) as transmission, patch.object(
                combats, 'prochain_avant_muraille') as selection:
            engagements = combats.enchainer_avants_muraille(
                (general,), object(), aleatoire=random.Random(3),
                camp='camp1', engager=lambda _: self.fail('Choc interdit'))
        self.assertEqual(engagements, ())
        transmission.assert_called_once_with('camp1')
        selection.assert_not_called()

    def test_muraille_arrete_apres_perte_qg_sans_interrompre_choc(self):
        from unittest.mock import patch
        import combats
        generaux = ({'id': 1}, {'id': 2})
        transmissions = [True, False]
        engages = []
        with patch.object(combats.ordres_pipeline, 'identite',
                          side_effect=lambda g: ('j1', f"g{g['id']}")), patch.object(
                combats, 'prochain_avant_muraille',
                return_value={'choisi': ('j1', 'g1'), 'previsions': ()}) as choisir:
            resultat = combats.enchainer_avants_muraille(
                generaux, object(), aleatoire=random.Random(1),
                engager=lambda g: engages.append(g['id']) or {'choc': True},
                transmission_active=lambda: transmissions.pop(0))
        self.assertEqual(engages, [1])
        self.assertEqual(resultat, ((('j1', 'g1'), {'choc': True}),))
        choisir.assert_called_once()

    def test_muraille_recalcule_apres_chaque_engagement(self):
        from unittest.mock import patch
        import combats

        a, b, c = ({'id': i} for i in (1, 2, 3))
        appels = []
        donnees = iter([
            {'choisi': ('j1', 'g2'), 'previsions': ()},
            {'choisi': ('j1', 'g3'), 'previsions': ()},
            {'choisi': ('j1', 'g1'), 'previsions': ()},
        ])

        def selection(disponibles, *_args, **_kwargs):
            appels.append(tuple(g['id'] for g in disponibles))
            return next(donnees)

        avec_identite = lambda g: ('j1', f"g{g['id']}")
        with patch.object(combats.ordres_pipeline, 'identite',
                          side_effect=avec_identite), patch.object(
                combats, 'prochain_avant_muraille', side_effect=selection):
            resultat = combats.enchainer_avants_muraille(
                (a, b, c), object(), aleatoire=random.Random(1),
                engager=lambda g: f"choc-{g['id']}")
        self.assertEqual(appels, [(1, 2, 3), (1, 3), (1,)])
        self.assertEqual(resultat, (
            (('j1', 'g2'), 'choc-2'),
            (('j1', 'g3'), 'choc-3'),
            (('j1', 'g1'), 'choc-1'),
        ))

    def test_muraille_selection_sarrete_si_plus_de_cible(self):
        from unittest.mock import patch
        import combats
        general = {'id': 1}
        with patch.object(combats.ordres_pipeline, 'identite',
                          return_value=('j1', 'g1')), patch.object(
                combats, 'prochain_avant_muraille',
                return_value={'choisi': None, 'previsions': ()}):
            self.assertEqual(combats.enchainer_avants_muraille(
                (general,), object(), aleatoire=random.Random(1),
                engager=lambda _g: self.fail('Engagement inattendu')), ())

    def test_muraille_meilleur_bilan_puis_position_numerique_origine(self):
        a, b = ('j1', 'general1'), ('j1', 'general2')
        positions = {a: '10', b: '2'}
        hasard = Mock()
        self.assertEqual(calculs.choisir_avant_muraille({a: 4, b: 3}, positions, hasard), a)
        self.assertEqual(calculs.choisir_avant_muraille({a: 4, b: 4}, positions, hasard), b)
        # Le nouvel engagement doit utiliser les bilans recalculés fournis.
        self.assertEqual(calculs.choisir_avant_muraille({a: -2, b: -1}, positions, hasard), b)
        self.assertIsNone(calculs.choisir_avant_muraille({}, {}, hasard))
        hasard.choice.assert_not_called()

    def test_muraille_egalite_hasard_reproductible_independant_du_parcours(self):
        a, b = ('j1', 'general1'), ('j2', 'general1')
        positions = {a: '2', b: '2'}
        choix = set()
        for graine in range(20):
            x = calculs.choisir_avant_muraille({a: 5, b: 5}, positions, random.Random(graine))
            y = calculs.choisir_avant_muraille({b: 5, a: 5}, positions, random.Random(graine))
            self.assertEqual(x, y)
            choix.add(x)
        self.assertEqual(choix, {a, b})

    def test_muraille_refuse_positions_et_bilans_invalides(self):
        identite = ('j1', 'general1')
        hasard = Mock()
        for position in (None, 'village', '0', '-1', '１'):
            with self.assertRaises(ValueError):
                calculs.choisir_avant_muraille({identite: 1}, {identite: position}, hasard)
        for bilan in (True, 1.5, '4'):
            with self.assertRaises(ValueError):
                calculs.choisir_avant_muraille({identite: bilan}, {identite: '1'}, hasard)
        hasard.choice.assert_not_called()

    def test_facteurs_moraux_exacts_et_entrees_invalides(self):
        from fractions import Fraction
        self.assertEqual(50 * calculs.facteur_cruelle(10), 45)
        self.assertEqual(31 * calculs.facteur_cruelle(10), Fraction(279, 10))
        self.assertEqual(calculs.facteur_discours_de_la_mort(Fraction(4692, 100)),
                         Fraction(12903, 250))
        for valeur in (True, -1, 2.5, '10'):
            with self.assertRaises(ValueError):
                calculs.facteur_cruelle(valeur)
            with self.assertRaises(ValueError):
                calculs.facteur_discours_de_la_mort(valeur)

    def test_charge_suicidaire_pertes_du_seul_duel(self):
        for pertes, attendu in ((0, 0), (3, 0), (4, 1),
                                (7, 1), (8, 2), (20, 5)):
            with self.subTest(pertes=pertes):
                self.assertEqual(calculs.probabilite_charge_suicidaire(pertes),
                                 attendu)

    def test_ralliement_par_type_arrondi_inferieur(self):
        self.assertEqual(calculs.renforts_ralliement(
            {"archer": 6, "piquier": 5},
            {"archer"}), {"archer": 1})
        self.assertEqual(calculs.renforts_ralliement(
            {"archer": 6, "piquier": 5},
            {"archer", "piquier"}), {"archer": 1, "piquier": 1})
        self.assertEqual(calculs.renforts_ralliement(
            {"archer": 4, "piquier": 15},
            {"archer", "piquier"}), {"archer": 0, "piquier": 3})

    def test_entiers_positifs_requis(self):
        for valeur in (-1, 1.2, True, "20"):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValueError):
                    calculs.probabilite_charge_suicidaire(valeur)
                with self.assertRaises(ValueError):
                    calculs.renforts_ralliement({"archer": valeur}, {"archer"})


    def test_discours_mort_pourcentage_de_la_valeur_actuelle(self):
        from fractions import Fraction
        self.assertEqual(calculs.facteur_discours_de_la_mort(30), 33)
        self.assertEqual(calculs.facteur_discours_de_la_mort(31), Fraction(341, 10))
        self.assertEqual(calculs.facteur_discours_de_la_mort(0), 0)
        # Ne jamais choisir arbitrairement l'arrondi à ce stade.
        self.assertEqual(calculs.facteur_discours_de_la_mort(99), Fraction(1089, 10))

    def test_reserve_interceptions_repetables(self):
        for _ in range(3):
            self.assertTrue(calculs.reserve_peut_intercepter(True, 5))
        self.assertFalse(calculs.reserve_peut_intercepter(False, 5))
        self.assertFalse(calculs.reserve_peut_intercepter(True, 0))
        self.assertFalse(calculs.reserve_peut_intercepter(True, 5, deja_elimine=True))

    def test_derniere_charge_defaite_obligatoire(self):
        self.assertFalse(calculs.derniere_charge_possible(False, "G"))
        self.assertTrue(calculs.derniere_charge_possible(True, "D"))
        with self.assertRaises(ValueError):
            calculs.derniere_charge_possible(True, "GD")

    def test_derniere_charge_casse_et_absence_sans_autre_flanc(self):
        for flanc in ('G', 'g', 'D', 'd'):
            self.assertTrue(calculs.derniere_charge_possible(True, flanc, effectif_eligible=1))
            self.assertFalse(calculs.derniere_charge_possible(False, flanc, effectif_eligible=1))
            self.assertFalse(calculs.derniere_charge_possible(True, flanc, effectif_eligible=0))
        for valeur in (-1, True, 1.5, '1'):
            with self.assertRaises(ValueError):
                calculs.derniere_charge_possible(True, 'g', effectif_eligible=valeur)
        for flanc in ('', 'gd', 'gauche', ' G ', None):
            with self.assertRaises(ValueError):
                calculs.derniere_charge_possible(True, flanc)


    def test_rafale_tentatives_par_quatre_archers(self):
        for archers, tirs in ((0, 0), (3, 0), (4, 1), (7, 1),
                             (8, 2), (20, 5)):
            self.assertEqual(calculs.tentatives_rafale(archers), tirs)

    def test_confinement_neutralise_spore_et_son_bonus(self):
        self.assertEqual(calculs.conversions_spore(1), 1)
        self.assertEqual(calculs.conversions_spore(1, True), 2)
        self.assertEqual(calculs.conversions_spore(1, True, True), 0)
        self.assertEqual(calculs.conversions_spore(1, False, True), 0)

    def test_propagation_bonus_deux(self):
        self.assertEqual(calculs.conversions_propagation(4), 4)
        self.assertEqual(calculs.conversions_propagation(4, True), 6)


if __name__ == "__main__":
    unittest.main()
