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

    def test_fatigue_heterogene_duel_reel_pertes_chez_les_origines(self):
        a, preteur, ennemi = self.scenario(type_adverse='piquier')
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        origines = copy.deepcopy(self.soldats.charger())
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            vue = self.vue(groupe, a)
            with patch.object(self.combats.rapports, 'afficher_et_ecrire') as rapport:
                resultat = self.duel(a, ennemi, vue)
            self.assertEqual((resultat['final_1'], resultat['final_2']), (2, 0))
            self.assertIn('j1 general1 : FATIGUE PARTIELLE (3/6 soldats)',
                          [appel.args[0] for appel in rapport.call_args_list])
            bilan = groupe.bilan()
            self.assertEqual(sum(len(b['pertes']) for b in bilan.values()), 4)
            self.assertTrue(bilan[('j1', 'general2', 'avant')]['pertes'])
            vivants = groupe._selection_vivante(None)
            self.assertEqual(vue.fatigues_individuelles(a, vue.blocs(a)['avant']),
                             tuple(p.general == preteur['nom'] for p in vivants))
        registre = self.soldats.charger()
        self.assertEqual(set(registre), set(origines))
        for identifiant, origine in origines.items():
            self.assertEqual(registre[identifiant]['chemin'], origine['chemin'])
            self.assertEqual(registre[identifiant]['batailles'], origine['batailles'])
        self.assertEqual(self.soldats._prets.get(), set())

    def verifier_cas_b(self, bloc):
        a = self.troupe('j1', 'piquier', 8)
        b = self.troupe('j2', 'piquier', 3, bloc=bloc)
        preteur = self.troupe('j2', 'piquier', 1, bloc=bloc, numero=2, place='2')
        for g in (a, b, preteur):
            self.ordres(g)
        self.etat.sauvegarder_generaux_fatigues({'j2:general2'})
        with self.soldats.participation_temporaire([
                self.contribution(b, bloc), self.contribution(preteur, bloc)]) as groupe:
            resultat = self.duel(a, b, self.vue(groupe, b, bloc))
            self.assertEqual((resultat['final_1'], resultat['final_2']), (5, 0))
            self.assertEqual(len(groupe.bilan()[('j2', 'general2', bloc)]['pertes']), 1)
        return resultat

    def test_cas_b_choc_surnombre_frais(self):
        self.assertEqual(self.verifier_cas_b('avant')['chocs'][0]['final_1'], 5)

    def test_cas_b_manoeuvre_surnombre_frais(self):
        resultat = self.verifier_cas_b('arriere')
        self.assertEqual(resultat['chocs'], [])
        self.assertEqual(resultat['manoeuvres'][0]['final_attaquant'], 5)

    def test_fatigue_heterogene_blessures_xp_et_droits_conserves(self):
        a, preteur, ennemi = self.scenario(type_adverse='piquier')
        self.ordres(a, moral=100)
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        with self.soldats.bataille_complete('fatigue-melangee'):
            with self.soldats.participation_temporaire([
                    self.contribution(a), self.contribution(preteur)]) as groupe:
                droits = {p.chemin: (p.uid, p.gid, p.chemin.stat().st_mode) for p in groupe.participants}
                ids = [p.identifiant for p in groupe.participants]
                resultat = self.duel(a, ennemi, self.vue(groupe, a))
                self.assertEqual((resultat['final_1'], resultat['final_2']), (6, 0))
                groupe.participer(ids)
        registre = self.soldats.charger()
        self.assertEqual({registre[i]['batailles'] for i in ids}, {1})
        self.assertEqual(sum(registre[i]['blessures'] for i in ids), 4)
        self.assertEqual(self.etat.charger_generaux_fatigues(), {'j1:general2'})
        for chemin, attendu in droits.items():
            infos = chemin.stat()
            self.assertEqual((infos.st_uid, infos.st_gid, infos.st_mode), attendu)

    def test_releve_individuel_3_et_5_par_uuid_sans_choisir_de_formule(self):
        generaux = [self.troupe(joueur, 'piquier', 5, numero=numero, place=str(numero))
                    for joueur in ('j1', 'j2') for numero in (1, 2)]
        a, preteur_a, b, preteur_b = generaux
        self.etat.sauvegarder_generaux_fatigues({'j1:general2', 'j2:general2'})
        avant = self.photo()
        with self.soldats.participation_temporaire([
                self.contribution(g) for g in generaux]) as groupe:
            ids = {(g['joueur'], g['nom']): tuple(p.identifiant for p in groupe.participants
                   if (p.joueur, p.general) == (g['joueur'], g['nom'])) for g in generaux}
            for n, fatigue_a, fatigue_b in ((3, 0, 0), (3, 3, 3), (3, 0, 3),
                                          (3, 1, 0), (5, 2, 0), (5, 2, 3)):
                with self.subTest(effectif=n, fatigue_a=fatigue_a, fatigue_b=fatigue_b):
                    affectations = []
                    for g, preteur, fatigues in ((a, preteur_a, fatigue_a), (b, preteur_b, fatigue_b)):
                        selection = (ids[g['joueur'], g['nom']][:n-fatigues]
                                     + ids[preteur['joueur'], preteur['nom']][:fatigues])
                        affectations.append((g, 'avant', selection))
                    vue = self.soldats.VueParticipants(groupe, affectations)
                    for g, fatigues in ((a, fatigue_a), (b, fatigue_b)):
                        infos = vue.blocs(g)['avant']
                        releve = vue.fatigues_individuelles(g, infos)
                        self.assertEqual(releve, (False,) * (n-fatigues) + (True,) * fatigues)
                        par_uuid = groupe.fatigues_origine(affectations[0 if g is a else 1][2])
                        self.assertEqual(releve, tuple(par_uuid[self.soldats.marqueur(u)]
                                                      for u in infos['unites']))
                    self.assertEqual(self.photo(), avant)
        self.assertEqual(self.photo(), avant)

    def test_releve_individuel_apres_perte_et_fermeture(self):
        a, preteur, _ = self.scenario()
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            vue = self.vue(groupe, a)
            fatigues = [p.identifiant for p in groupe.participants if p.general == preteur['nom']]
            groupe.appliquer_pertes(fatigues[:1], 0, moral=0, aleatoire=random.Random(0))
            infos = vue.blocs(a)['avant']
            self.assertEqual(vue.fatigues_individuelles(a, infos), (False,) * 3 + (True,) * 2)
            self.assertEqual(set(groupe.fatigues_origine(fatigues)), set(fatigues[1:]))
            self.assertEqual(self.etat.charger_generaux_fatigues(), {'j1:general2'})
        with self.assertRaises(RuntimeError):
            vue.fatigues_individuelles(a, infos)

    def test_releve_ordinaire_et_bloc_vide(self):
        a, _, _ = self.scenario()
        vue = self.soldats.VueParticipants()
        for fatigue in (False, True):
            self.etat.sauvegarder_generaux_fatigues({'j1:general1'} if fatigue else set())
            infos = vue.blocs(a)
            self.assertEqual(vue.fatigues_individuelles(a, infos['avant']), (fatigue,) * 3)
            self.assertEqual(vue.fatigues_individuelles(a, infos['arriere']), ())
            self.assertEqual(vue.fatigue(a, infos['arriere']), fatigue)

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

    def test_fatigue_recalculee_sur_les_survivants_de_rafale(self):
        a, preteur, ennemi = self.scenario(type_adverse='piquier')
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        for n in range(4):
            self.speciale(ennemi, 'archer', n, 'arriere')
        self.ordres(ennemi, [1009])
        calcul = self.combats.combat_bloc
        releves = []

        def observer(infos_1, infos_2, fatigue_1, fatigue_2, *args, **kwargs):
            releves.append((infos_1['nombre'], fatigue_1, infos_2['nombre'], fatigue_2))
            return calcul(infos_1, infos_2, fatigue_1, fatigue_2, *args, **kwargs)

        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            with patch.object(self.combats, 'combat_bloc', side_effect=observer):
                resultat = self.duel(a, ennemi, self.vue(groupe, a))
        self.assertEqual(resultat['rafales'][0]['pertes'], 1)
        self.assertEqual(releves[0], (5, (False,) * 3 + (True,) * 2, 2, False))

    def test_interruption_apres_choc_heterogene_sans_duplication(self):
        a, preteur, ennemi = self.scenario(type_adverse='piquier')
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        identites = set(self.soldats.charger())
        with self.assertRaisesRegex(RuntimeError, 'interruption après choc'):
            with self.soldats.bataille_complete('fatigue-interrompue'):
                with self.soldats.participation_temporaire([
                        self.contribution(a), self.contribution(preteur)]) as groupe:
                    vue = self.vue(groupe, a)
                    with patch.object(self.combats.ordres_pipeline, 'fuir_apres_choc',
                                      side_effect=RuntimeError('interruption après choc')):
                        self.duel(a, ennemi, vue)
        registre = self.soldats.charger()
        self.assertEqual(set(registre), identites)
        self.assertEqual(sum(bool(v.get('detruit')) for v in registre.values()), 6)
        self.assertEqual({v['batailles'] for v in registre.values()}, {0})
        self.assertEqual(self.soldats._prets.get(), set())
        with self.assertRaises(RuntimeError):
            vue.total(a)

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

    def test_gros_poisson_vue_partielle_fatigue_pertes_retour_et_preteur_suivant(self):
        a, preteur, ennemi = self.scenario(type_adverse='piquier')
        natif_non_fusionne, _ = self.speciale(a, 'archer', 10, 'droite')
        prete_non_fusionne, _ = self.speciale(preteur, 'cavalier', 10, 'droite')
        self.etat.sauvegarder_generaux_fatigues({'j1:general2'})
        contributions = [self.contribution(g, bloc) for g in (a, preteur)
                         for bloc in ('avant', 'droite')]
        origines = copy.deepcopy(self.soldats.charger())
        with self.soldats.participation_temporaire(contributions) as groupe:
            vue, motif = groupe.vue_gros_poisson(a, preteur, self.profil)
            self.assertIsNone(motif)
            self.assertEqual(vue.total(a), 7)
            self.assertEqual(vue.total(preteur), 1)
            self.assertEqual(vue.blocs(a)['droite']['unites'], [natif_non_fusionne])
            resultat = self.duel(a, ennemi, vue)
            self.assertEqual((resultat['final_1'], resultat['final_2']), (3, 0))
            self.assertEqual(sum(len(v['pertes']) for v in groupe.bilan().values()), 4)
            self.assertTrue(prete_non_fusionne.is_dir())
        self.assertEqual(self.soldats._prets.get(), set())
        registre = self.soldats.charger()
        self.assertEqual(set(registre), set(origines))
        for identifiant, origine in origines.items():
            self.assertEqual(registre[identifiant]['chemin'], origine['chemin'])
        effectif_preteur = self.generaux.total_general_depuis_chemin(preteur['chemin'])
        autre = self.troupe('j2', 'cavalier', 1, numero=2, place='2')
        self.ordres(autre)
        suivant = self.duel(preteur, autre)
        self.assertEqual(suivant['initial_1'], effectif_preteur)

    def test_gros_poisson_vue_sans_homologue_motif_sans_mutation(self):
        a = self.troupe('j1', 'piquier', 3)
        preteur = self.troupe('j1', 'archer', 3, numero=2, place='2')
        avant = self.photo()
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            vue, motif = groupe.vue_gros_poisson(a, preteur, self.profil)
            self.assertIn('sans effet', motif)
            self.assertEqual((vue.total(a), vue.total(preteur)), (3, 3))
            self.assertEqual(self.photo(), avant)
        self.assertEqual(self.photo(), avant)

    def test_gros_poisson_vue_reutilise_les_restrictions_zombie(self):
        a, preteur, _ = self.scenario()
        registre = self.progression.charger()
        registre['j1:general2']['etat_zombie'] = True
        self.progression.sauvegarder(registre)
        avant = self.photo()
        with self.soldats.participation_temporaire([
                self.contribution(a), self.contribution(preteur)]) as groupe:
            with self.assertRaisesRegex(ValueError, 'Profil privé'):
                groupe.vue_gros_poisson(a, preteur, self.profil)
        self.assertEqual(self.photo(), avant)

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
