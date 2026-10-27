"""Ordres acquis dans de véritables duels, sur des plateaux temporaires."""
import copy
from fractions import Fraction
import random
import unittest
from unittest.mock import patch

import test_unites_v2
import ordres_pipeline


class EffetsOrdres(unittest.TestCase):
    setUp = test_unites_v2.UnitesV2.setUp
    activer = test_unites_v2.UnitesV2.activer
    general = test_unites_v2.UnitesV2.general
    creer = test_unites_v2.UnitesV2.creer
    infos = test_unites_v2.UnitesV2.infos
    modules = test_unites_v2.UnitesV2.modules
    speciale = test_unites_v2.UnitesV2.speciale

    def troupe(self, joueur, type_unite, nombre=4, bloc='avant', numero=1, place='1'):
        chemin = self.general(joueur, numero=numero, territoire='est_3', place=place, nombre=0)
        general = dict(joueur=joueur, nom=chemin.name, chemin=chemin, emplacement=place)
        for n in range(nombre):
            self.speciale(general, type_unite, n, bloc)
        return general

    def ordres(self, general, ids=(), texte=None, moral=0, pc=20, **autres):
        donnees = self.progression.charger()
        cle = ':'.join(ordres_pipeline.identite(general))
        donnees[cle].update(nature='instinctif', moral=moral, points_commandement=pc,
                            evolutions_acquises=list(ids), **autres)
        self.progression.sauvegarder(donnees)
        if texte is None:
            texte = '\n'.join(self.combats.catalogues.ORDRES[i]['jeton'] for i in ids)
        (general['chemin'] / 'ordre.txt').write_text(texte, encoding='utf-8')

    def duel(self, a, b):
        with patch.object(self.combats, 'random', random.Random(3)):
            return self.combats.combat_entre_generaux(a, b)

    def test_herisson_duel_reel_deux_camps_et_identites(self):
        for joueur in ('j1', 'j2'):
            numero = 1 if joueur == 'j1' else 2
            a = self.troupe(joueur, 'piquier', numero=numero, place=str(numero))
            b = self.troupe('j2' if joueur == 'j1' else 'j1', 'cavalier',
                            numero=numero, place=str(numero))
            self.ordres(a, [1006])
            self.ordres(b)
            identites = {self.soldats.marqueur(u) for u in self.infos(a)['unites']}
            r = self.duel(a, b)
            self.assertEqual((r['final_1'], r['final_2']), (3, 0))
            self.assertEqual(r['chocs'][0]['final_1'], 3)
            survivants = {self.soldats.marqueur(u) for u in self.infos(a)['unites']}
            self.assertTrue(survivants < identites)
            self.assertEqual({self.soldats.charger()[i]['batailles'] for i in survivants}, {0})

    def test_herisson_faiblesse_distance_egalement_augmente(self):
        a, b = self.troupe('j1', 'piquier', 6), self.troupe('j2', 'orc_archer', 4)
        self.ordres(a, [1006]); self.ordres(b)
        r = self.duel(a, b)
        self.assertEqual((r['chocs'][0]['final_1'], r['chocs'][0]['final_2']), (0, 3))

    def test_non_appris_memoire_et_fiche_falsifiee_ne_donnent_aucun_droit(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier')
        self.ordres(a, texte='3-2', evolution_apprise=1006)
        self.ordres(b)
        a['caracteristiques'] = dict(nature='instinctif', evolutions_acquises=[1006])
        with (a['chemin'] / 'fiche.txt').open('a') as f:
            f.write('\nevolutions_acquises=1006\n')
        r = self.duel(a, b)
        self.assertEqual((r['final_1'], r['final_2']), (2, 0))
        self.assertNotIn('ordres_v2', r)

    def test_parametres_non_definis_ne_sont_pas_des_cibles_implicites(self):
        a, b = self.troupe('j1', 'piquier', numero=12), self.troupe('j2', 'cavalier')
        self.ordres(a, [1006, 1008], texte='3-2-1\n2-3-1')
        self.ordres(b)
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertEqual(decisions, [])

    def test_general_zombie_et_profil_absent_ne_donnent_pas_d_ordres(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier')
        self.ordres(a, [1006], etat_zombie=True); self.ordres(b)
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertFalse(decisions)
        registre = self.progression.charger()
        del registre['j1:general1']
        self.progression.sauvegarder(registre)
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertFalse(decisions)

    def test_opposition_personnelle_egalite_annule_et_pc_superieur_gagne(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier')
        self.ordres(a, [1006], pc=20); self.ordres(b, [1007], pc=20)
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertEqual([d['retenus'] for d in decisions], [[], []])
        self.ordres(a, [1006], pc=21)
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertEqual([d['retenus'] for d in decisions], [[1006], []])

    def test_cumul_personnel_sans_ordre_du_voisin(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier')
        voisin = self.troupe('j1', 'archer', numero=2, place='2')
        self.ordres(a, [1006, 1007]); self.ordres(b); self.ordres(voisin, [1009])
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertEqual(decisions[0]['retenus'], [1006, 1007])
            self.assertFalse(ordres_pipeline.effet(a, 'rafale'))
            self.assertFalse(ordres_pipeline.effet(voisin, 'rafale'))

    def test_discours_exact_plafond_et_aucune_mutation_persistante(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier')
        self.ordres(a, [1007], moral=31); self.ordres(b)
        avant = copy.deepcopy(self.progression.charger())
        for _ in range(2):
            with ordres_pipeline.duel(a, b):
                self.assertEqual(ordres_pipeline.moral(a, 31), Fraction(341, 10))
                self.assertEqual(ordres_pipeline.moral(a, Fraction(4692, 100)), Fraction(12903, 250))
                self.assertEqual(ordres_pipeline.moral(a, 99), 100)
        self.assertEqual(self.progression.charger(), avant)

    def test_discours_sauve_reellement_une_unite_supplementaire(self):
        a, b = self.troupe('j1', 'piquier', 20), self.troupe('j2', 'cavalier')
        self.ordres(a, [1007], moral=46); self.ordres(b)
        identites = {self.soldats.marqueur(u) for u in self.infos(a)['unites']}
        with ordres_pipeline.duel(a, b):
            pertes = self.combats.supprimer_unites(self.infos(a), 0, a)
        self.assertEqual(len(pertes), 10)  # 20 * 50,6 // 100, au lieu de 9 sauvetages.
        survivants = self.infos(a)['unites']
        self.assertTrue({self.soldats.marqueur(u) for u in survivants} < identites)
        self.assertTrue(all(self.soldats.charger()[self.soldats.marqueur(u)]['blessures'] == 1
                            for u in survivants))

    def test_orc_temporaire_moral_chaman_et_identites_inchangees(self):
        a, b = self.troupe('j1', 'sauvageon', 6), self.troupe('j2', 'orc_chaman')
        self.ordres(a, [1008], moral=50); self.ordres(b)
        avant = copy.deepcopy(self.soldats.charger())
        composition = self.generaux.lire_composition_general(a['chemin'])
        fiche = self.progression.caracteristiques_general(a)
        with ordres_pipeline.duel(a, b):
            self.assertTrue(self.unites.etiquette('sauvageon', 'orc', a))
            self.assertFalse(self.unites.etiquette('sauvageon', 'orc', b))
            self.assertEqual(self.unites.caracteristiques_armee(fiche, composition, a)['moral'], 46)
            self.assertEqual(self.combats.multiplicateur('sauvageon', 'orc_chaman', a, b), 1)
            self.assertEqual(self.combats.multiplicateur('orc_chaman', 'sauvageon', b, a), 3)
        self.assertFalse(self.unites.etiquette('sauvageon', 'orc', a))
        self.assertEqual(self.soldats.charger(), avant)

    def test_orc_duel_reel_et_pas_de_transformation_de_recette(self):
        a, b = self.troupe('j1', 'sauvageon', 8), self.troupe('j2', 'orc_chaman', 1)
        self.ordres(a, [1008]); self.ordres(b)
        r = self.duel(a, b)
        self.assertEqual((r['final_1'], r['final_2']), (6, 0))
        self.assertEqual(self.infos(a)['type'], 'sauvageon')
        self.assertTrue(all((u / 'sauvageon.txt').exists() for u in self.infos(a)['unites']))

    def test_interruption_reinitialise_les_effets_et_le_duel_suivant(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier')
        self.ordres(a, [1006]); self.ordres(b)
        with patch.object(self.combats, 'phase_engagement_initial', side_effect=RuntimeError('incident')):
            with self.assertRaisesRegex(RuntimeError, 'incident'):
                self.duel(a, b)
        self.assertIsNone(ordres_pipeline._duel.get())
        self.assertIsNone(self.unites._duel.get())
        self.assertEqual(self.duel(a, b)['final_1'], 3)

    def test_rafale_moral_conserve_victime_blessee_et_uuid(self):
        a, b = self.troupe('j1', 'archer', 4, 'arriere'), self.troupe('j2', 'piquier', 1)
        self.ordres(a, [1009]); self.ordres(b, moral=100)
        unite = self.infos(b)['unites'][0]
        identifiant = self.soldats.marqueur(unite)
        with ordres_pipeline.duel(a, b):
            details = ordres_pipeline.rafales(a, b, random.Random(1), self.combats.supprimer_unites)
        self.assertEqual((details[0]['touches'], details[0]['pertes']), (1, 0))
        self.assertTrue(unite.exists())
        self.assertEqual(self.soldats.marqueur(unite), identifiant)
        self.assertEqual(self.soldats.charger()[identifiant]['blessures'], 1)

    def test_rafale_armure_lourde_immunisee(self):
        a, b = self.troupe('j1', 'archer', 8, 'arriere'), self.troupe('j2', 'cavalerie_lourde')
        self.ordres(a, [1009]); self.ordres(b)
        avant = copy.deepcopy(self.soldats.charger())
        with ordres_pipeline.duel(a, b):
            details = ordres_pipeline.rafales(a, b, random.Random(1), self.combats.supprimer_unites)
        self.assertEqual((details[0]['tirs'], details[0]['touches'], details[0]['pertes']), (2, 0, 0))
        self.assertEqual(self.soldats.charger(), avant)

    def test_rafale_precede_bouclier_sans_le_desactiver(self):
        a, b = self.troupe('j1', 'archer', 4, 'arriere'), self.troupe('j2', 'zombie', 3)
        self.speciale(b, 'Trop_gros_zombie', bloc='arriere')
        self.ordres(a, [1009]); self.ordres(b)
        import bouclier_vivant
        priorite = bouclier_vivant.resoudre_priorite
        vus = []
        def verifier(zombie, ennemi):
            vus.append(self.infos(zombie)['nombre'])
            self.assertTrue(bouclier_vivant.presence_bouclier(zombie))
            return priorite(zombie, ennemi)
        with patch.object(bouclier_vivant, 'resoudre_priorite', side_effect=verifier), \
                patch.object(self.combats.random, 'sample', side_effect=lambda seq, n: list(seq)[:n]):
            r = self.combats.combat_entre_generaux(a, b)
        self.assertEqual(vus, [2])
        self.assertEqual(r['rafales'][0]['pertes'], 1)
        self.assertTrue(any(d['moment'] == 'Bouclier vivant' for d in r['chocs']))

    def test_rafale_sans_arriere_archer_et_seuil_ne_tire_pas(self):
        a, b = self.troupe('j1', 'archer', 8), self.troupe('j2', 'cavalier')
        self.ordres(a, [1009]); self.ordres(b)
        with ordres_pipeline.duel(a, b):
            self.assertEqual(ordres_pipeline.rafales(a, b, random.Random(1), self.combats.supprimer_unites), [])
        for n in range(3):
            self.speciale(a, 'archer', n, 'arriere')
        with ordres_pipeline.duel(a, b):
            self.assertEqual(ordres_pipeline.rafales(a, b, random.Random(1), self.combats.supprimer_unites), [])

    def test_rafale_duel_reel_dans_les_deux_sens(self):
        for joueur, numero in (('j1', 1), ('j2', 2)):
            a = self.troupe(joueur, 'archer', 8, 'arriere', numero, str(numero))
            b = self.troupe('j2' if joueur == 'j1' else 'j1', 'piquier', 1,
                            'avant', numero, str(numero))
            self.ordres(a, [1009]); self.ordres(b)
            r = self.duel(b, a)
            self.assertEqual((r['initial_1'], r['final_1'], r['final_2']), (1, 0, 8))
            self.assertFalse(r['chocs'])
            self.assertFalse(r['manoeuvres'])

    def test_rafale_elimine_avant_choc_et_compte_bataille_des_survivants(self):
        a, b = self.troupe('j1', 'archer', 8, 'arriere'), self.troupe('j2', 'piquier', 1)
        self.ordres(a, [1009]); self.ordres(b)
        ids = {self.soldats.marqueur(u) for u in self.generaux.lire_blocs_general(a['chemin'])['arriere']['unites']}
        with self.soldats.bataille_complete('rafale:eliminee'):
            r = self.duel(a, b)
        self.assertEqual(r['final_2'], 0)
        self.assertEqual({self.soldats.charger()[i]['batailles'] for i in ids}, {1})

    def test_duel_allie_refuse_avant_toute_rafale(self):
        a, b = self.troupe('j1', 'archer', 4, 'arriere'), self.troupe('j2', 'piquier', 1)
        self.ordres(a, [1009]); self.ordres(b)
        a['camp'] = b['camp'] = 'allies'
        avant = copy.deepcopy(self.soldats.charger())
        with self.assertRaises(ValueError):
            self.duel(a, b)
        self.assertEqual(self.soldats.charger(), avant)

    def test_discours_et_rafale_cumules_dans_un_combat_reel(self):
        a, b = self.troupe('j1', 'archer', 8, 'arriere'), self.troupe('j2', 'piquier', 4)
        self.ordres(a, [1007, 1009], moral=31); self.ordres(b)
        r = self.duel(a, b)
        self.assertEqual(r['ordres_v2'][0]['retenus'], [1007, 1009])
        self.assertEqual(r['rafales'][0]['pertes'], 2)

    def test_herisson_en_manoeuvre_sans_choc_initial(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier', bloc='arriere')
        self.ordres(a, [1006]); self.ordres(b)
        r = self.duel(a, b)
        self.assertFalse(r['chocs'])
        self.assertEqual((r['final_1'], r['final_2']), (3, 0))

    def test_non_regression_1_2_avec_pipeline_vide(self):
        from contextlib import contextmanager
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier')
        self.ordres(a, texte='1-2'); self.ordres(b)
        territory = self.config.game_path / 'est_3'
        profil = dict(self.profil)
        profil['acteurs'] = {j: dict(profil['acteurs'][j], camp=j) for j in ('j1', 'j2')}
        @contextmanager
        def ancien(*args):
            yield []
        engagements = []
        # Même moteur territorial et mêmes demandes, effet de duel remplacé
        # par un observateur sans pertes pour comparer les deux parcours.
        def observer(g1, g2, *, participants=None):
            engagements.append((g1['joueur'], g1['nom'], g2['joueur'], g2['nom']))
            return dict(joueur_1=g1['joueur'], joueur_2=g2['joueur'],
                general_1=g1['nom'], general_2=g2['nom'], initial_1=4, initial_2=4,
                final_1=4, final_2=4, chocs=[], manoeuvres=[])
        with patch.object(self.combats, '_combat_entre_generaux', side_effect=observer):
            self.combats.resoudre_affrontement_actif(territory, 'OFF/OFF', profil)
            nouveau = list(engagements)
            engagements.clear()
            with patch.object(ordres_pipeline, 'duel', ancien):
                self.combats.resoudre_affrontement_actif(territory, 'OFF/OFF', profil)
        self.assertEqual(engagements, nouveau)
        self.assertEqual(len(nouveau), 21)  # Un frontal puis 20 rounds bornés.

    def preparation_tour_rafale(self):
        a = self.troupe('j1', 'archer', 8, 'arriere')
        self.ordres(a, [1009])
        self.general('bot', numero=99, territoire='est_3', nombre=4, equipement='pique')
        self.activer(0)
        self.rapports.preparer_rapports(self.profil)
        self.rapports.ecrire_rapport_court('ANCIEN TOUR')
        avant = {p: p.read_bytes() for p in self.config.rapport_dir.rglob('*') if p.is_file()}
        return avant

    def test_tour_complet_rapports_ordres_prives_jusqua_publication(self):
        avant = self.preparation_tour_rafale()
        origine = ordres_pipeline.rafales
        executions = []
        def verifier(a, b, hasard, pertes, *, participants=None):
            resultat = origine(a, b, hasard, pertes, participants=participants)
            if resultat:
                executions.append(resultat)
                self.assertEqual({p: p.read_bytes() for p in avant}, avant)
            return resultat
        with patch.object(ordres_pipeline, 'rafales', side_effect=verifier), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, random.Random(4))
        self.assertTrue(executions)
        rapport = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertIn('Rafale', rapport)
        self.assertIn('rafale', rapport)
        self.assertNotIn('demandes', rapport)
        self.assertNotIn("'pc'", rapport)
        self.assertIn('Confrontation V2', self.config.rapport_long_path.read_text())

    def test_interruption_apres_rafale_privee_ne_publie_pas_et_interdit_rejeu(self):
        avant = self.preparation_tour_rafale()
        soldats_avant = copy.deepcopy(self.soldats.charger())
        origine = ordres_pipeline.rafales
        def interrompre(a, b, hasard, pertes, *, participants=None):
            resultat = origine(a, b, hasard, pertes, participants=participants)
            if resultat:
                raise RuntimeError('interruption après Rafale')
            return resultat
        with patch.object(ordres_pipeline, 'rafales', side_effect=interrompre), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'interruption après Rafale'):
                self.survie.resoudre_tour_survie(self.profil, random.Random(4))
        self.assertEqual({p: p.read_bytes() for p in avant}, avant)
        self.assertEqual(self.soldats.charger(), soldats_avant)
        self.assertIsNone(ordres_pipeline._duel.get())
        with patch.object(ordres_pipeline, 'rafales') as effet:
            with self.assertRaises(RuntimeError):
                self.survie.resoudre_tour_survie(self.profil, random.Random(4))
            effet.assert_not_called()

    def test_cruelle_facteur_exact_deux_camps_et_cumul_discours(self):
        for joueur, numero in (('j1', 1), ('j2', 2)):
            a = self.troupe(joueur, 'sauvageon', 10, numero=numero, place=str(numero))
            b = self.troupe('j2' if joueur == 'j1' else 'j1', 'piquier',
                            numero=numero, place=str(numero))
            self.ordres(a, [1010]); self.ordres(b, [1007], moral=50)
            with ordres_pipeline.duel(a, b):
                self.assertEqual(ordres_pipeline.moral(b, 50), Fraction(99, 2))
                self.assertEqual(ordres_pipeline.moral(a, 50), 50)
            self.ordres(b, moral=50)
            with ordres_pipeline.duel(a, b):
                self.assertEqual(ordres_pipeline.moral(b, 50), 45)
                self.assertEqual(ordres_pipeline.moral(b, 31), Fraction(279, 10))

    def test_cruelle_reduit_sauvetages_reels_sans_modifier_progression(self):
        a, b = self.troupe('j1', 'sauvageon', 10), self.troupe('j2', 'piquier', 20)
        self.ordres(a, [1010]); self.ordres(b, moral=50)
        with ordres_pipeline.duel(a, b):
            self.assertEqual(len(self.combats.supprimer_unites(self.infos(b), 0, b)), 11)
        self.assertEqual(self.progression.caracteristiques_general(b)['moral'], 50)

    def test_cruelle_duel_reel_reduit_le_sauvetage_du_choc(self):
        a, b = self.troupe('j1', 'sauvageon', 10), self.troupe('j2', 'piquier', 20)
        self.ordres(a, [1010]); self.ordres(b, moral=50)
        resultat = self.duel(b, a)
        self.assertEqual((resultat['final_1'], resultat['final_2']), (16, 0))
        self.assertEqual(resultat['ordres_v2'][0]['retenus'], [1010])
        self.assertEqual(self.progression.caracteristiques_general(b)['moral'], 50)

    def test_cruelle_cumul_duel_et_decompte_initial_fige(self):
        a, b = self.troupe('j1', 'sauvageon', 10), self.troupe('j2', 'piquier')
        self.ordres(a, [1008, 1010]); self.ordres(b, moral=50)
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertEqual(decisions[0]['retenus'], [1008, 1010])
            self.combats.supprimer_unites(self.infos(a), 5, a)
            self.assertEqual(ordres_pipeline.moral(b, 50), 45)
        with ordres_pipeline.duel(a, b):
            self.assertEqual(ordres_pipeline.moral(b, 50), Fraction(95, 2))

    def test_cruelle_sans_unites_cruelles_et_ordre_perdu_sans_effet(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'sauvageon')
        self.ordres(a, [1010], pc=10); self.ordres(b, [1008], pc=20, moral=50)
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertEqual(decisions[0]['retenus'], [])
            self.assertEqual(ordres_pipeline.moral(b, 50), 50)
        self.ordres(b, moral=50)
        with ordres_pipeline.duel(a, b):
            self.assertEqual(ordres_pipeline.moral(b, 50), 50)

    def partie_ordres(self, joueurs, graine, archers):
        from test_audit_v2 import AuditParties
        creer = self.general
        resultats = []
        combat = self.combats.combat_entre_generaux
        def installer(*args, **kwargs):
            if archers:
                kwargs['equipement'] = 'arc'
            chemin = creer(*args, **kwargs)
            if archers:
                for u in (chemin / 'avant').iterdir():
                    u.rename(chemin / 'arriere' / u.name)
            self.ordres(dict(joueur=args[0], nom=chemin.name, chemin=chemin),
                        [1006, 1007, 1008, 1009, 1010], moral=31)
            return chemin
        def observer(*args):
            r = combat(*args)
            resultats.append(r)
            return r
        with patch.object(self, 'general', side_effect=installer), \
                patch.object(self.combats, 'combat_entre_generaux', side_effect=observer):
            AuditParties.partie(self, joueurs, graine)
        self.assertTrue(any(r.get('ordres_v2') for r in resultats))
        if archers:
            self.assertTrue(any(r.get('rafales') for r in resultats))

    def test_partie_complete_avec_rafale_discours_et_reprise(self):
        self.partie_ordres(('j1',), 17, True)

    def test_partie_cooperative_avec_ordres_et_reprise(self):
        self.partie_ordres(('j1', 'j2'), 31, False)


if __name__ == '__main__':
    unittest.main()
