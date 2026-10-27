"""Même duel et vraies pertes avec une sélection explicite, sans activer d'ordre."""
import copy
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import test_ordres_effets_v2 as aides
import test_participations_temporaires as groupes


class VueParticipants(unittest.TestCase):
    setUp = aides.EffetsOrdres.setUp
    activer = aides.EffetsOrdres.activer
    general = aides.EffetsOrdres.general
    creer = aides.EffetsOrdres.creer
    infos = aides.EffetsOrdres.infos
    modules = aides.EffetsOrdres.modules
    speciale = aides.EffetsOrdres.speciale
    troupe = aides.EffetsOrdres.troupe
    ordres = aides.EffetsOrdres.ordres
    contribution = groupes.ParticipationsTemporaires.contribution
    photo = groupes.ParticipationsTemporaires.photo

    def scenario(self, bloc_adverse='avant', type_adverse='cavalier'):
        a = self.troupe('j1', 'piquier', 3)
        preteur = self.troupe('j1', 'piquier', 3, numero=2, place='2')
        # Deux cavaliers infligent floor(2 * 5 / 10) = une perte aux piquiers.
        ennemi = self.troupe('j2', type_adverse, 2, bloc=bloc_adverse)
        for general in (a, preteur, ennemi):
            self.ordres(general)
        return a, preteur, ennemi

    def vue(self, groupe, commandant, bloc='avant'):
        ids = tuple(p.identifiant for p in groupe.participants)
        return self.soldats.VueParticipants(groupe, [(commandant, bloc, ids)])

    def duel(self, a, b, vue=None):
        with patch.object(self.combats, 'random', random.Random(0)):
            return self.combats.combat_entre_generaux(a, b, participants=vue)

    def test_lecture_origines_commandant_sans_engagement_et_bloc_absent(self):
        a, preteur, _ = self.scenario()
        contributions = [self.contribution(a), self.contribution(preteur)]
        (a['chemin'] / 'droite').rmdir()
        avant = self.photo()
        with self.soldats.bataille_complete('lecture-seule'):
            with self.soldats.participation_temporaire(contributions) as groupe:
                vue = self.vue(groupe, a)
                self.assertEqual(vue.total(a), 6)
                self.assertEqual(vue.total(preteur), 0)
                self.assertEqual(len({p.identifiant for p in groupe.participants}), 6)
                self.assertEqual({p.general for p in groupe.participants}, {'general1', 'general2'})
                self.assertEqual({p.bloc for p in groupe.participants}, {'avant'})
                self.assertEqual(self.photo(), avant)
        self.assertEqual(self.photo(), avant)
        with self.assertRaises(RuntimeError):
            vue.blocs(a)

    def test_choc_perte_reelle_chez_preteur_et_duel_suivant(self):
        a, preteur, ennemi = self.scenario()
        origines = copy.deepcopy(self.soldats.charger())
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            resultat = self.duel(a, ennemi, self.vue(groupe, a))
            self.assertEqual((resultat['initial_1'], resultat['final_1'], resultat['final_2']), (6, 5, 0))
            self.assertEqual(resultat['chocs'][0]['initial_1'], 6)
            bilan = groupe.bilan()
            self.assertEqual(len(bilan[('j1', 'general2', 'avant')]['pertes']), 1)
            self.assertEqual(len(bilan[('j1', 'general1', 'avant')]['survivants']), 3)
        self.assertEqual(self.infos(preteur)['nombre'], 2)
        autre = self.troupe('j2', 'cavalier', 2, numero=2, place='2')
        self.ordres(autre)
        suivant = self.duel(preteur, autre)
        self.assertEqual((suivant['initial_1'], suivant['final_1']), (2, 1))
        registre = self.soldats.charger()
        for identifiant, valeur in origines.items():
            self.assertEqual(registre[identifiant]['chemin'], valeur['chemin'])
            self.assertEqual(registre[identifiant]['type'], valeur['type'])
        self.assertEqual(self.soldats._prets.get(), set())

    def test_manoeuvre_utilise_selection_et_non_dossiers_du_commandant(self):
        a, preteur, ennemi = self.scenario('arriere')
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            resultat = self.duel(a, ennemi, self.vue(groupe, a))
            self.assertEqual(resultat['chocs'], [])
            self.assertEqual(resultat['manoeuvres'][0]['initial_attaquant'], 6)
            self.assertEqual((resultat['final_1'], resultat['final_2']), (5, 0))
            self.assertEqual(sum(len(b['survivants']) for b in groupe.bilan().values()), 5)

    def test_fatigue_origine_homogene_differente_du_commandant(self):
        a, preteur, ennemi = self.scenario(type_adverse='piquier')
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        # Sélection du seul prêteur : les soldats natifs restent hors du duel.
        with self.soldats.participation_temporaire([self.contribution(preteur)]) as groupe:
            vue = self.vue(groupe, a)
            self.assertTrue(vue.fatigue(a, vue.blocs(a)['avant']))
            natifs = set(self.infos(a)['unites'])
            resultat = self.duel(a, ennemi, vue)
            self.assertEqual(resultat['initial_1'], 3)
            self.assertEqual((resultat['final_1'], resultat['final_2']), (0, 1))
            self.assertTrue(all(p.is_dir() for p in natifs))
        self.assertFalse(self.etat.general_est_fatigue(a))
        self.assertTrue(self.etat.general_est_fatigue(preteur))

    def test_fatigue_heterogene_refusee_avant_perte_rapport_et_hasard(self):
        a, preteur, ennemi = self.scenario()
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        avant, rng = self.photo(), random.Random(8)
        hasard = rng.getstate()
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            with patch.object(self.combats, 'random', rng):
                with self.assertRaisesRegex(NotImplementedError, 'Fatigue hétérogène'):
                    self.combats.combat_entre_generaux(a, ennemi, participants=self.vue(groupe, a))
        self.assertEqual((self.photo(), rng.getstate()), (avant, hasard))

    def test_capacite_ambigue_refusee_avant_mutation(self):
        a, preteur, ennemi = self.scenario()
        self.speciale(ennemi, 'Trop_gros_zombie', 1, 'arriere')
        avant = self.photo()
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            with self.assertRaisesRegex(NotImplementedError, 'Capacités/composition'):
                self.duel(a, ennemi, self.vue(groupe, a))
        self.assertEqual(self.photo(), avant)

    def test_blessures_moral_commandant_xp_unique_sans_credit_preteur(self):
        a, preteur, ennemi = self.scenario()
        self.ordres(a, moral=100)
        profil_preteur = copy.deepcopy(self.progression.caracteristiques_general(preteur))
        with self.soldats.bataille_complete('vue-xp'):
            with self.soldats.participation_temporaire([
                    self.contribution(a), self.contribution(preteur)]) as groupe:
                ids = [p.identifiant for p in groupe.participants]
                resultat = self.duel(a, ennemi, self.vue(groupe, a))
                self.assertEqual(resultat['final_1'], 6)
                groupe.participer(ids)  # Une seconde inscription ne double pas l’XP.
        registre = self.soldats.charger()
        self.assertEqual({registre[i]['batailles'] for i in ids}, {1})
        self.assertEqual(sum(registre[i]['blessures'] for i in ids), 1)
        self.assertEqual(self.progression.caracteristiques_general(preteur), profil_preteur)

    def test_rafale_cible_les_pretes_et_rapporte_effectifs_engages(self):
        a, preteur, ennemi = self.scenario()
        for n in range(4):
            self.speciale(ennemi, 'archer', n, 'arriere')
        self.ordres(ennemi, [1009])
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            resultat = self.duel(a, ennemi, self.vue(groupe, a))
            self.assertEqual(resultat['initial_1'], 6)
            self.assertEqual(resultat['rafales'][0]['pertes'], 1)
            self.assertEqual(resultat['chocs'][0]['initial_1'], 5)
            self.assertTrue(groupe.bilan()[('j1', 'general2', 'avant')]['pertes'])

    def test_affectation_dupliquee_etrangere_ou_adverse_refusee(self):
        a, preteur, ennemi = self.scenario()
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            ids = [p.identifiant for p in groupe.participants]
            with self.assertRaises(ValueError):
                self.soldats.VueParticipants(groupe, [(a, 'avant', ids), (preteur, 'avant', ids)])
            with self.assertRaises(ValueError):
                self.soldats.VueParticipants(groupe, [(a, 'avant', ['inconnu'])])
            with self.assertRaisesRegex(ValueError, 'camp adverse'):
                self.duel(a, ennemi, self.vue(groupe, ennemi))
            with self.assertRaisesRegex(RuntimeError, 'vue explicite'):
                self.duel(a, ennemi)

    def test_interruption_ne_restaure_pas_les_pertes_et_ne_credite_pas_xp(self):
        a, preteur, ennemi = self.scenario()
        ids = set(self.soldats.charger())
        with self.assertRaisesRegex(RuntimeError, 'interruption après choc'):
            with self.soldats.bataille_complete('interrompue'):
                with self.soldats.participation_temporaire([
                        self.contribution(a), self.contribution(preteur)]) as groupe:
                    vue = self.vue(groupe, a)
                    with patch.object(self.combats.ordres_pipeline, 'fuir_apres_choc',
                                      side_effect=RuntimeError('interruption après choc')):
                        self.duel(a, ennemi, vue)
        registre = self.soldats.charger()
        self.assertEqual(sum(bool(registre[i].get('detruit')) for i in ids), 3)
        self.assertEqual({registre[i]['batailles'] for i in ids}, {0})
        self.assertEqual(self.soldats._prets.get(), set())
        self.assertIsNone(self.combats.ordres_pipeline._duel.get())
        with self.assertRaises(RuntimeError):
            vue.total(a)

    def test_commandant_sans_natifs_survit_avec_les_pretes(self):
        a = self.troupe('j1', 'piquier', 1)
        preteur = self.troupe('j1', 'piquier', 5, numero=2, place='2')
        ennemi = self.troupe('j2', 'cavalier', 2)
        for g in (a, preteur, ennemi):
            self.ordres(g)
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            vue = self.vue(groupe, a)
            # Seed 2 choisit le seul natif parmi les six participants.
            with patch.object(self.combats, 'random', random.Random(2)):
                resultat = self.combats.combat_entre_generaux(a, ennemi, participants=vue)
            self.assertEqual(self.infos(a)['nombre'], 0)
            self.assertEqual(resultat['final_1'], 5)
            self.assertTrue(a['chemin'].is_dir())
        self.assertEqual(self.infos(preteur)['nombre'], 5)

    def test_ordres_lot_b_restent_inactifs(self):
        noms = {'gros_poisson', 'muraille_humaine', 'ralliement', 'derniere_charge'}
        self.assertFalse(any(o['disponible'] and o['nom'] in noms
                             for o in self.combats.catalogues.ORDRES.values()))

    def test_duel_prive_publie_origines_pertes_xp_et_rapport(self):
        a = self.troupe('j1', 'piquier', 3)
        preteur = self.troupe('j1', 'piquier', 3, numero=2, place='2')
        self.troupe('bot', 'cavalier', 2, numero=99)
        self.ordres(a)
        self.ordres(preteur)
        self.activer(0)
        identites = set(self.soldats.charger())
        public = self.photo()
        original = self.combats.combat_entre_generaux
        executions = []

        def engager(g1, g2):
            if (g1['joueur'], g1['nom']) != ('j1', a['nom']):
                return original(g1, g2)
            self.assertTrue(self.config.dans_generation_privee())
            copie = dict(preteur, chemin=self.config.racine_metier() /
                         preteur['chemin'].relative_to(self.config.game_path))
            with self.soldats.participation_temporaire([
                    self.contribution(g1), self.contribution(copie)]) as groupe:
                resultat = original(g1, g2, participants=self.vue(groupe, g1))
                executions.append(resultat)
                # Le public garde encore tous les soldats, y compris les morts privés.
                for origine in (a, preteur):
                    self.assertEqual(len(list((origine['chemin'] / 'avant').iterdir())), 3)
                return resultat

        with patch.object(self.combats, 'combat_entre_generaux', side_effect=engager), \
                patch.object(self.combats, 'random', random.Random(0)), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, random.Random(0))
        self.assertEqual(len(executions), 1)
        self.assertEqual((executions[0]['initial_1'], executions[0]['final_1']), (6, 5))
        self.assertEqual((self.infos(a)['nombre'], self.infos(preteur)['nombre']), (3, 2))
        registre = self.soldats.charger()
        self.assertEqual(set(registre), identites)
        survivants = [v for v in registre.values() if not v.get('detruit')]
        self.assertEqual(len(survivants), 5)
        self.assertEqual({v['batailles'] for v in survivants}, {1})
        rapport = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertIn('6 → 5', rapport)
        self.assertNotEqual(self.photo(), public)


if __name__ == '__main__':
    unittest.main()
