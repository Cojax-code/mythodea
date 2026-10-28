"""Prêts réels du QG et capacités communes, exclusivement sur plateaux temporaires."""
import copy
from fractions import Fraction
import random
import unittest
from unittest.mock import Mock, patch

import test_qg_effets_v2 as aides
import ordres_pipeline


class GrosPoisson(unittest.TestCase):
    setUp = aides.EffetsQG.setUp
    activer = aides.EffetsQG.activer
    general = aides.EffetsQG.general
    creer = aides.EffetsQG.creer
    infos = aides.EffetsQG.infos
    modules = aides.EffetsQG.modules
    speciale = aides.EffetsQG.speciale
    troupe = aides.EffetsQG.troupe
    ordres = aides.EffetsQG.ordres
    declarer = aides.EffetsQG.declarer
    bataille = aides.EffetsQG.bataille

    def scenario(self, type_unite='piquier', natifs=3, pretes=3, adverse='cavalier', ennemis=2):
        a = self.troupe('j1', type_unite, natifs)
        p = self.troupe('j1', type_unite, pretes, numero=2, place='2')
        b = self.troupe('j2', adverse, ennemis)
        self.ordres(a)
        self.ordres(b)
        self.ordres(p, [1017], texte='2-6-1-2')
        self.declarer(p)
        return a, p, b

    def duel(self, a, b):
        with self.bataille(), patch.object(self.combats, 'random', random.Random(0)):
            return self.combats.combat_entre_generaux(a, b)

    def vue(self, a, p):
        generaux = self.combats.generaux
        return self.soldats.participation_temporaire([
            (g, bloc, generaux.chemins_bloc(infos)) for g in (a, p)
            for bloc, infos in generaux.lire_blocs_general(g['chemin']).items()])

    def test_qg_pret_perte_uuid_retour_et_duel_suivant(self):
        a, p, b = self.scenario()
        avant = copy.deepcopy(self.soldats.charger())
        resultat = self.duel(a, b)
        self.assertEqual((resultat['initial_1'], resultat['final_1'], resultat['final_2']), (6, 5, 0))
        self.assertEqual(self.infos(p)['nombre'], 2)
        decision = next(d for d in resultat['ordres_v2'] if 1017 in d['retenus'])
        self.assertEqual(decision['donneur_general'], 'general2')
        for identifiant, valeur in avant.items():
            self.assertEqual(self.soldats.charger()[identifiant]['chemin'], valeur['chemin'])
        autre = self.troupe('j2', 'cavalier', 2, numero=2, place='2')
        self.ordres(autre)
        self.assertEqual(self.duel(p, autre)['initial_1'], 2)
        self.assertFalse(self.soldats._prets.get())

    def test_self_target_ne_constitue_pas_de_groupe(self):
        a, p, b = self.scenario()
        self.ordres(p, [1017], texte='2-6-1-1')
        self.ordres(b, [1010], pc=1)
        with patch.object(self.soldats, 'participation_temporaire', side_effect=AssertionError('aucun prêt')):
            resultat = self.duel(a, b)
        self.assertEqual(resultat['initial_1'], 3)
        self.assertFalse(any(1017 in d['demandes'] for d in resultat['ordres_v2']))
        self.assertTrue(any(1010 in d['retenus'] for d in resultat['ordres_v2']))

    def test_plusieurs_preteurs_fusion_unique_doublons_et_auto_designation(self):
        a, p, b = self.scenario('cavalerie_lourde', 5, 5)
        autre = self.troupe('j1', 'cavalerie_lourde', 5, numero=3, place='3')
        self.ordres(autre)
        self.ordres(p, [1017], texte='2-6-1-2\n2-6-1-3\n2-6-1-2\n2-6-1-1')
        with self.bataille(), ordres_pipeline.duel(a, b) as decisions:
            with ordres_pipeline.participations_duel(a, b, self.soldats.VueParticipants(), decisions) as vue:
                infos = vue.blocs(a)['avant']
                self.assertEqual(infos['nombre'], 15)
                self.assertEqual(len(set(infos['unites'])), 15)
                self.assertEqual(self.combats.valeur_base_bloc(infos, 'avant'), 10)
                self.assertEqual(vue.total(p), 0)
                self.assertEqual(vue.total(autre), 0)
                self.assertEqual(len(vue.groupe.participants), 15)
        self.assertEqual([self.infos(g)['nombre'] for g in (a, p, autre)], [5, 5, 5])
        resultat = self.duel(a, b)
        self.assertEqual(resultat['initial_1'], 15)

    def test_preteur_deux_beneficiaires_detection_avant_constitution(self):
        a, p, b = self.scenario()
        contexte = {ordres_pipeline.identite(a): {'gros_poisson': [(a, p)]},
                    ordres_pipeline.identite(b): {'gros_poisson': [(b, p)]}}
        # Injection d'une configuration incohérente : aucune priorité arbitraire,
        # aucun UUID réservé avant détection. Les vrais duels filtrent les camps.
        with self.bataille(), patch.object(ordres_pipeline, '_duel') as contexte_duel:
            contexte_duel.get.return_value = contexte
            with patch.object(self.soldats, 'participation_temporaire', side_effect=AssertionError('duplication')):
                with self.assertRaisesRegex(ValueError, 'conflictuel'):
                    with ordres_pipeline.participations_duel(a, b, self.soldats.VueParticipants(), []):
                        pass
        self.assertFalse(self.soldats._prets.get())

    def test_plusieurs_preteurs_types_absents_ignores_et_fatigue_par_origine(self):
        a, p, b = self.scenario()
        autre = self.troupe('j1', 'archer', 4, numero=3, place='3')
        self.speciale(a, 'archer', 0, 'arriere')
        self.speciale(autre, 'archer', 0, 'arriere')
        self.ordres(autre)
        self.ordres(p, [1017], texte='2-6-1-2\n2-6-1-3')
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        with self.bataille(), ordres_pipeline.duel(a, b) as decisions:
            with ordres_pipeline.participations_duel(a, b, self.soldats.VueParticipants(), decisions) as vue:
                avant = vue.blocs(a)['avant']
                self.assertEqual(vue.fatigues_individuelles(a, avant), (False,) * 3 + (True,) * 3)
                self.assertEqual(vue.blocs(a)['arriere']['nombre'], 2)
                self.assertEqual(vue.blocs(autre)['avant']['nombre'], 4)
        self.assertEqual(self.etat.charger_generaux_fatigues(), {'j1:general2'})

    def test_absence_qg_apprentissage_position_ou_profil_interdit(self):
        a, p, b = self.scenario()
        for texte, appris, qg, zombie in (
                ('2-6-1-2', [], True, False), ('2-6-1-2', [1017], False, False),
                ('2-6-1-9', [1017], True, False), ('2-6-1-2', [1017], True, True)):
            with self.subTest(texte=texte, appris=appris, qg=qg, zombie=zombie):
                self.ordres(p, appris, texte=texte, etat_zombie=zombie)
                self.declarer(p)
                if not qg:
                    (p['chemin'] / 'qg.txt').unlink()
                with self.bataille(), ordres_pipeline.duel(a, b) as decisions:
                    self.assertFalse(ordres_pipeline.effet(a, 'gros_poisson'))

    def test_types_distincts_sans_homologue_motif_et_aucune_perte_preteur(self):
        a, p, b = self.scenario()
        self.combats.supprimer_unites(self.infos(p), 0, p)
        self.speciale(p, 'archer', 20)
        avant = copy.deepcopy(self.soldats.charger())
        resultat = self.duel(a, b)
        self.assertEqual(resultat['initial_1'], 3)
        self.assertIn('aucune unité homologue', resultat['ordres_v2'][0]['motif'])
        for identifiant, valeur in avant.items():
            if 'general2/' in valeur['chemin']:
                self.assertEqual(self.soldats.charger()[identifiant], valeur)

    def test_formation_lourde_10_plus_5_et_recalcul_sous_15(self):
        a, p, b = self.scenario('cavalerie_lourde', 10, 5)
        with self.vue(a, p) as groupe:
            vue, _ = groupe.vue_gros_poisson(a, p, self.profil)
            infos = vue.blocs(a)['avant']
            self.assertEqual(infos['nombre'], 15)
            self.assertEqual(self.combats.valeur_base_bloc(infos, 'avant'), 10)
            self.combats.supprimer_unites(infos, 14, a, participants=vue)
            infos = vue.blocs(a)['avant']
            self.assertEqual(self.combats.valeur_base_bloc(infos, 'avant'), 5)

    def test_chaman_prete_soutient_orcs_sans_soin_premature(self):
        a, p, b = self.scenario('orc_assaillant', 5, 5)
        self.speciale(a, 'orc_chaman', 1, 'arriere')
        self.speciale(p, 'orc_chaman', 1, 'arriere')
        self.ordres(a, moral=50)
        with self.vue(a, p) as groupe:
            vue, _ = groupe.vue_gros_poisson(a, p, self.profil)
            self.assertEqual(vue.composition(a)['arriere'], {'orc_chaman': 2})
            # 12 Orcs => moral 52 ; deux chamans dans un autre bloc => *1,04.
            self.assertEqual(self.combats.moral_des_pertes(vue.blocs(a)['avant'], a, participants=vue),
                             Fraction(1352, 25))
        with patch.object(self.unites, 'soigner_victoire_territoriale', side_effect=AssertionError('trop tôt')):
            self.duel(a, b)

    def test_messagers_dans_bloc_combat_et_pertes_chez_origines(self):
        a, p, b = self.scenario()
        natif, nid = self.speciale(a, 'messager_du_QG', 1)
        prete, pid = self.speciale(p, 'messager_du_QG', 1)
        profils = copy.deepcopy(self.progression.charger())
        with self.vue(a, p) as groupe:
            vue, _ = groupe.vue_gros_poisson(a, p, self.profil)
            infos = vue.blocs(a)['avant']
            self.assertEqual(infos['nombre'], 6)
            self.assertEqual(set(infos['soutiens']), {natif, prete})
            self.assertEqual(vue.total(a), 8)
            self.assertEqual(vue.total(p), 0)
            self.combats.supprimer_unites(infos, 0, a, participants=vue)
            self.assertTrue(all(self.soldats.charger()[i]['detruit'] for i in (nid, pid)))
        self.assertEqual(self.progression.charger(), profils)

    def test_soutien_reserve_interdit_au_duel_sans_vue(self):
        a, p, b = self.scenario()
        soutien, _ = self.speciale(a, 'messager_du_QG', 1)
        with self.soldats.participation_temporaire([(a, 'avant', [soutien])]):
            with self.assertRaisesRegex(RuntimeError, 'vue explicite'):
                self.combats.combat_entre_generaux(a, b)

    def test_spore_convertit_un_prete_sans_restitution_ni_perte_uuid(self):
        a, p, b = self.scenario(adverse='zombie', ennemis=1)
        registre = self.soldats.charger()
        victime = self.infos(p)['unites'][0]
        identifiant = self.soldats.marqueur(victime)
        for valeur in registre.values():
            valeur['batailles'] = 5
        registre[identifiant]['batailles'] = 0
        self.soldats.sauvegarder(registre)
        with self.vue(a, p) as groupe:
            vue, _ = groupe.vue_gros_poisson(a, p, self.profil)
            obtenu = self.combats.bouclier_vivant.convertir_spore(b, a, 'avant', 'pret:spore',
                                                               random.Random(0), participants=vue)
            self.assertEqual(obtenu, identifiant)
            self.assertFalse(victime.exists())
            self.assertEqual(vue.total(a), 5)
            self.assertEqual(vue.total(b), 2)
            self.assertEqual(len(groupe.bilan()[('j1', 'general2', 'avant')]['pertes']), 1)
        valeur = self.soldats.charger()[identifiant]
        self.assertIn('j2/1/general1/avant/', valeur['chemin'])
        self.assertEqual(valeur['type'], 'zombie')
        self.assertEqual(self.infos(p)['nombre'], 2)

    def test_placement_zombies_majorite_egalite_et_arriere_sans_zombie(self):
        g = self.troupe('j1', 'zombie', 2)
        self.speciale(g, 'messager_du_QG', 1, 'arriere')
        rng = Mock()
        self.assertEqual(self.unites.bloc_destination_zombies(g, rng), 'avant')
        rng.choice.assert_not_called()
        for n in range(2):
            self.speciale(g, 'zombie', n, 'droite')
        rng.choice.return_value = 'droite'
        self.assertEqual(self.unites.bloc_destination_zombies(g, rng), 'droite')
        self.assertEqual(set(rng.choice.call_args.args[0]), {'avant', 'droite'})
        vide = self.troupe('j1', 'piquier', 1, numero=2, place='2')
        self.assertEqual(self.unites.bloc_destination_zombies(vide, rng), 'arriere')

    def test_propagation_place_chez_source_dans_majorite_et_ne_rejoue_pas(self):
        g = self.troupe('j1', 'zombie', 1)
        for n in range(3):
            self.speciale(g, 'zombie', n, 'droite')
        self.assertEqual(self.unites.propager(g, 'avant', 4, 1, 'majorite', 'duel'), 2)
        composition = self.combats.generaux.lire_composition_general(g['chemin'])
        self.assertEqual(composition['avant'], {'zombie': 1})
        self.assertEqual(composition['droite'], {'zombie': 5})
        self.assertEqual(self.unites.propager(g, 'avant', 4, 1, 'majorite', 'duel'), 0)

    def test_zombies_exclus_du_pret_et_du_discours_meme_general_ordinaire(self):
        a, p, b = self.scenario('zombie')
        with self.vue(a, p) as groupe:
            self.assertEqual(groupe.selections_gros_poisson(a, p, self.profil)['selections'], {})
        self.ordres(a, [1007], moral=50)
        with ordres_pipeline.duel(a, b):
            self.assertEqual(ordres_pipeline.moral(a, 50, type_unite='zombie'), 50)
            self.assertEqual(ordres_pipeline.moral(a, 50, type_unite='piquier'), 55)

    def test_choca_fuite_libere_le_pret_avant_deplacement(self):
        a, p, b = self.scenario(ennemis=1)
        self.ordres(p, [1017, 1011], texte='2-6-1-2\n2-5')
        callback = Mock(return_value=[dict(joueur='j1', general='general1')])
        with ordres_pipeline.retraites_apres_choc(callback):
            resultat = self.duel(a, b)
        callback.assert_called_once()
        self.assertFalse(self.soldats._prets.get())
        self.assertEqual(self.infos(p)['nombre'], 3)

    def test_choca_sans_natifs_ne_reserve_pas_un_general_supprime_au_retour(self):
        a, p, b = self.scenario(natifs=1, pretes=5)
        self.ordres(p, [1017, 1011], texte='2-6-1-2\n2-5')
        callback = Mock(side_effect=AssertionError('retraite sans troupe propre'))
        with self.bataille(), ordres_pipeline.retraites_apres_choc(callback), \
                patch.object(self.combats, 'random', random.Random(2)):
            resultat = self.combats.combat_entre_generaux(a, b)
        callback.assert_not_called()
        self.assertFalse(a['chemin'].exists())
        self.assertEqual(self.infos(p)['nombre'], 5)
        self.assertFalse(resultat.get('fuites'))

    def test_confrontation_perdue_empeche_le_pret(self):
        a, p, b = self.scenario()
        self.ordres(b, [1010], pc=100)
        resultat = self.duel(a, b)
        self.assertEqual(resultat['initial_1'], 3)
        self.assertTrue(any(1017 in d['demandes'] and 1017 not in d['retenus']
                            for d in resultat['ordres_v2']))
        self.assertEqual(self.infos(p)['nombre'], 3)

    def test_cruelle_recalcule_apres_fusion_complete_du_qg_beneficiaire(self):
        a, p, b = self.scenario('orc_assaillant', 5, 5)
        (p['chemin'] / 'qg.txt').unlink()
        self.declarer(a)
        self.ordres(p)
        self.ordres(a, [1017, 1010], texte='2-6-1-2\n2-4')
        with self.bataille(), ordres_pipeline.duel(a, b) as decisions:
            with ordres_pipeline.participations_duel(a, b, self.soldats.VueParticipants(), decisions):
                self.assertEqual(ordres_pipeline.moral(b, 50), 45)

    def test_gros_poisson_adverses_s_annulent_a_pc_egaux(self):
        a, p, b = self.scenario(ennemis=3, adverse='piquier')
        q = self.troupe('j2', 'piquier', 3, numero=2, place='2')
        self.ordres(q, [1017], texte='2-6-1-2')
        self.declarer(q)
        with self.bataille(), ordres_pipeline.duel(a, b) as decisions:
            with ordres_pipeline.participations_duel(a, b, self.soldats.VueParticipants(), decisions) as vue:
                self.assertEqual([vue.total(g) for g in (a, p, b, q)], [3, 3, 3, 3])
                self.assertIsNone(vue.groupe)
                self.assertTrue(all(1017 not in d['retenus'] for d in decisions))
                for g in (a, b):
                    self.assertTrue(all(g['joueur'] in chemin.parts for chemin in vue.blocs(g)['avant']['unites']))
        self.assertEqual([self.infos(g)['nombre'] for g in (a, p, b, q)], [3, 3, 3, 3])

    def test_fatigue_blessures_xp_et_proprietes_pendant_pipeline_reel(self):
        a, p, b = self.scenario(adverse='piquier')
        self.ordres(a, moral=100)
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        chemins = [*self.infos(a)['unites'], *self.infos(p)['unites']]
        ids = [self.soldats.marqueur(c) for c in chemins]
        droits = [(c.stat().st_uid, c.stat().st_gid, c.stat().st_mode) for c in chemins]
        with self.soldats.bataille_complete('pret:xp'):
            resultat = self.duel(a, b)
        self.assertEqual(resultat['final_1'], 6)
        registre = self.soldats.charger()
        self.assertEqual({registre[i]['batailles'] for i in ids}, {1})
        self.assertGreater(sum(registre[i]['blessures'] for i in ids), 0)
        self.assertEqual(self.etat.charger_generaux_fatigues(), {'j1:general2'})
        self.assertEqual([(c.stat().st_uid, c.stat().st_gid, c.stat().st_mode) for c in chemins], droits)

    def test_survie_positions_logiques_preteur_autre_joueur(self):
        a = self.troupe('j1', 'piquier', 3)
        p = self.troupe('j2', 'piquier', 3, place='2')
        b = self.troupe('bot', 'cavalier', 2)
        self.ordres(a)
        self.ordres(p, [1017], texte='2-6-1-2')
        self.declarer(p)
        with ordres_pipeline.bataille(self.config.game_path / 'est_3', self.profil):
            resultat = self.combats.combat_entre_generaux(a, b)
        self.assertEqual((resultat['initial_1'], resultat['final_1'], resultat['final_2']), (6, 5, 0))
        self.assertTrue(all('j2/2/general1/' in v['chemin'] for v in self.soldats.charger().values()
                            if 'j2/' in v['chemin']))


if __name__ == '__main__':
    unittest.main()
