"""Infrastructure préparatoire du lot B ; aucun ordre réservé n'est activé."""
import copy
import os
from pathlib import Path
import random
import shutil
import unittest
from unittest.mock import patch

import test_ordres_effets_v2 as aides
import ordres_calculs_v2


class ParticipationsTemporaires(unittest.TestCase):
    setUp = aides.EffetsOrdres.setUp
    activer = aides.EffetsOrdres.activer
    general = aides.EffetsOrdres.general
    creer = aides.EffetsOrdres.creer
    infos = aides.EffetsOrdres.infos
    modules = aides.EffetsOrdres.modules
    speciale = aides.EffetsOrdres.speciale
    troupe = aides.EffetsOrdres.troupe

    def contribution(self, g, bloc='avant'):
        return g, bloc, self.generaux.lire_blocs_general(g['chemin'])[bloc]['unites']

    def photo(self):
        return {p.relative_to(self.config.game_path).as_posix():
                (p.read_bytes() if p.is_file() else None,
                 p.stat().st_ino, p.stat().st_uid, p.stat().st_gid, p.stat().st_mode)
                for p in self.config.game_path.rglob('*')}

    def deux_generaux(self):
        return (self.troupe('j1', 'piquier', 3),
                self.troupe('j2', 'piquier', 3, place='2'))

    def test_preparation_et_restitution_virtuelle_sans_aucune_ecriture(self):
        a, b = self.deux_generaux()
        avant = self.photo()
        with self.soldats.participation_temporaire([self.contribution(a), self.contribution(b)]) as groupe:
            self.assertEqual(groupe.bloc()['nombre'], 6)
            self.assertEqual(set(groupe.bilan()), {('j1', 'general1', 'avant'), ('j2', 'general1', 'avant')})
            self.assertEqual(len({p.identifiant for p in groupe.participants}), 6)
            self.assertEqual(self.photo(), avant)
            # Les listes remises à l'appelant ne changent pas le groupe interne.
            groupe.bloc()['unites'].clear()
            self.assertEqual(groupe.bloc()['nombre'], 6)
        self.assertEqual(self.photo(), avant)
        self.assertEqual(self.soldats._prets.get(), set())

    def test_perte_explicitement_designee_reste_chez_son_proprietaire(self):
        a, b = self.deux_generaux()
        avant = copy.deepcopy(self.soldats.charger())
        with self.soldats.participation_temporaire([self.contribution(a), self.contribution(b)]) as groupe:
            victime = groupe.participants[3]
            self.soldats.pertes(groupe.bloc([victime.identifiant]), 0, aleatoire=random.Random(2))
            bilan = groupe.bilan()
            self.assertEqual(bilan[('j2', 'general1', 'avant')]['pertes'], (victime,))
            self.assertEqual(len(bilan[('j1', 'general1', 'avant')]['survivants']), 3)
            self.assertEqual(groupe.bloc()['nombre'], 5)
        apres = self.soldats.charger()
        self.assertEqual(apres[victime.identifiant], dict(avant[victime.identifiant], detruit=True))
        for identifiant in avant.keys() - {victime.identifiant}:
            self.assertEqual(apres[identifiant], avant[identifiant])
        self.assertFalse(victime.chemin.exists())
        self.assertTrue(a['chemin'].is_dir())
        self.assertTrue(b['chemin'].is_dir())

    def test_blessures_xp_et_champs_individuels_jamais_restaures(self):
        a, b = self.deux_generaux()
        registre = self.soldats.charger()
        for valeur in registre.values():
            valeur.update(batailles=7, blessures=1, historique_personnel={'test': [1, 2]})
        self.soldats.sauvegarder(registre)
        with self.soldats.participation_temporaire([self.contribution(a), self.contribution(b)]) as groupe:
            self.soldats.pertes(groupe.bloc(), 0, 100, random.Random(2))
            self.assertEqual(groupe.bloc()['nombre'], 6)
        for valeur in self.soldats.charger().values():
            self.assertEqual((valeur['blessures'], valeur['batailles']), (2, 7))
            self.assertEqual(valeur['historique_personnel'], {'test': [1, 2]})
        with self.soldats.participation_temporaire([self.contribution(a), self.contribution(b)]) as groupe:
            self.soldats.pertes(groupe.bloc(), 0, 100, random.Random(2))
            self.assertEqual(groupe.bloc(), dict(type='vide', nombre=0, unites=[]))
            self.assertEqual(sum(len(b['pertes']) for b in groupe.bilan().values()), 6)
        self.assertTrue(all(v['detruit'] for v in self.soldats.charger().values()))

    def test_tirage_existant_reproductible_sans_priorite_de_proprietaire(self):
        resultats = []
        for numero in (1, 2):
            a = self.troupe('j1', 'piquier', 4, numero=numero, place=str(numero))
            b = self.troupe('j2', 'piquier', 4, numero=numero, place=str(numero))
            with self.soldats.participation_temporaire([self.contribution(a), self.contribution(b)]) as groupe:
                self.soldats.pertes(groupe.bloc(), 3, 0, random.Random(23))
                resultats.append([(p.joueur, p.chemin.name)
                                  for bilan in groupe.bilan().values() for p in bilan['pertes']])
        self.assertEqual(resultats[0], resultats[1])

    def test_melange_de_types_exige_selection_sans_supprimer_minorite(self):
        a = self.troupe('j1', 'piquier', 3)
        b = self.troupe('j2', 'archer', 1, place='2')
        avant = self.photo()
        with self.soldats.participation_temporaire([self.contribution(a), self.contribution(b)]) as groupe:
            with self.assertRaisesRegex(ValueError, 'Composition mixte'):
                groupe.bloc()
            self.assertEqual(groupe.bloc([groupe.participants[-1].identifiant])['type'], 'archer')
        self.assertEqual(self.photo(), avant)

    def test_doublons_et_groupes_simultanes_refuses_sans_reservation_residuelle(self):
        a, b = self.deux_generaux()
        ca, cb = self.contribution(a), self.contribution(b)
        with self.assertRaises(ValueError):
            with self.soldats.participation_temporaire([ca, ca]):
                self.fail('Un doublon est entré dans le groupe.')
        with self.soldats.participation_temporaire([ca]) as groupe:
            with self.assertRaises(ValueError):
                with self.soldats.participation_temporaire([cb, ca]):
                    self.fail('Un prêt simultané a été accepté.')
            with self.soldats.participation_temporaire([cb]) as autre:
                self.assertEqual(autre.bloc()['nombre'], 3)
            self.assertEqual(groupe.bloc()['nombre'], 3)
        self.assertEqual(self.soldats._prets.get(), set())

    def test_exception_libere_vue_sans_annuler_pertes_reelles(self):
        a = self.troupe('j1', 'piquier', 3)
        with self.assertRaisesRegex(RuntimeError, 'interruption'):
            with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
                self.soldats.pertes(groupe.bloc(), 2, aleatoire=random.Random(3))
                raise RuntimeError('interruption')
        with self.assertRaisesRegex(RuntimeError, 'fermée'):
            groupe.bilan()
        self.assertEqual(len(self.infos(a)['unites']), 2)
        with self.soldats.participation_temporaire([self.contribution(a)]) as nouveau:
            self.assertEqual(nouveau.bloc()['nombre'], 2)

    def test_selection_etrangere_ou_repetee_refusee(self):
        a = self.troupe('j1', 'piquier')
        with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
            identifiant = groupe.participants[0].identifiant
            for ids in ([identifiant, identifiant], ['inconnu']):
                with self.assertRaises(ValueError):
                    groupe.bloc(ids)

    def test_selections_homologues_gardent_blocs_types_et_tous_les_uuid(self):
        a, b = self.deux_generaux()
        self.speciale(a, 'archer', 20, 'droite')
        self.speciale(b, 'archer', 20, 'avant')
        # Contribution explicite de chaque type, sans lecture majoritaire du bloc.
        contributions = [(g, bloc, list((g['chemin'] / bloc).iterdir()))
                         for g, bloc in ((a, 'avant'), (a, 'droite'), (b, 'avant'))]
        avant = self.photo()
        with self.soldats.participation_temporaire(contributions) as groupe:
            selections = groupe.selections_homologues()
            self.assertEqual({cle: len(ids) for cle, ids in selections.items()},
                             {('avant', 'piquier'): 6, ('avant', 'archer'): 1,
                              ('droite', 'archer'): 1})
            self.assertEqual({i for ids in selections.values() for i in ids},
                             {p.identifiant for p in groupe.participants})
            with self.assertRaises(AttributeError):
                groupe.participants = ()
            selections.clear()
            self.assertEqual(len(groupe.selections_homologues()), 3)
        self.assertEqual(self.photo(), avant)

    def test_calcul_combat_commun_et_pertes_reelles_sans_politique_d_ordre(self):
        a, b = self.deux_generaux()
        adverse = self.troupe('bot', 'cavalier', 4)
        with self.soldats.participation_temporaire([self.contribution(a), self.contribution(b)]) as groupe:
            ids = groupe.selections_homologues()[('avant', 'piquier')]
            instantane = groupe.bloc(ids)
            ennemi = self.infos(adverse)
            survivants, survivants_adverses = self.combats.combat_bloc(
                instantane, ennemi, False, False, 'avant', 'avant')
            self.assertEqual((survivants, survivants_adverses), (4, 0))
            pertes = groupe.appliquer_pertes(ids, survivants, moral=0, aleatoire=random.Random(7))
            self.combats.supprimer_unites(ennemi, survivants_adverses)
            self.assertEqual(len(pertes), 2)
            self.assertEqual(groupe.bloc(ids)['nombre'], 4)
            self.assertEqual(instantane['nombre'], 6)  # Instantané, pas état vivant.
            self.assertEqual(sum(len(v['pertes']) for v in groupe.bilan().values()), 2)
            with self.assertRaisesRegex(ValueError, 'survivants'):
                groupe.appliquer_pertes(ids, 5, moral=0)
        self.assertEqual(sum(len(self.infos(g)['unites']) for g in (a, b)), 4)

    def test_pertes_controlees_refusent_les_entrees_invalides_sans_ecriture(self):
        a = self.troupe('j1', 'piquier', 1)
        with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
            ids = [groupe.participants[0].identifiant]
            avant = self.photo()
            for selection, survivants, moral in (
                    (None, 0, 0), (ids * 2, 0, 0), (['inconnu'], 0, 0),
                    (ids, -1, 0), (ids, 2, 0), (ids, True, 0),
                    (ids, 0.5, 0), (ids, 0, 101)):
                with self.subTest(selection=selection, survivants=survivants, moral=moral):
                    with self.assertRaises(ValueError):
                        groupe.appliquer_pertes(selection, survivants, moral=moral)
                    self.assertEqual(self.photo(), avant)

    def test_selection_morte_ne_recree_rien_et_vue_fermee_ne_peut_plus_agir(self):
        a = self.troupe('j1', 'piquier', 1)
        with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
            ids = [groupe.participants[0].identifiant]
            groupe.appliquer_pertes(ids, 0, moral=0)
            apres = self.photo()
            self.assertEqual(groupe.selections_homologues(), {})
            self.assertEqual(groupe.appliquer_pertes(ids, 0, moral=100), [])
            self.assertEqual(self.photo(), apres)
        for action in (groupe.selections_homologues,
                       lambda: groupe.appliquer_pertes(ids, 0, moral=0),
                       lambda: groupe.participer(ids)):
            with self.assertRaisesRegex(RuntimeError, 'fermée'):
                action()
        self.assertEqual(self.photo(), apres)

    def test_participation_expresse_xp_commune_une_fois_sans_credit_au_preteur(self):
        a, b = self.deux_generaux()
        progression = copy.deepcopy(self.progression.charger())
        with self.soldats.bataille_complete('lot-b:territoire'):
            with self.soldats.participation_temporaire([self.contribution(a), self.contribution(b)]) as groupe:
                ids = [p.identifiant for p in groupe.participants]
                # Un seul soldat prêté est engagé ; une autre unité reste en réserve.
                selection = ids[:4]
                groupe.participer(selection)
                groupe.participer(selection)
                groupe.appliquer_pertes([ids[0]], 0, moral=0)
                groupe.appliquer_pertes([ids[3]], 0, moral=100)
        registre = self.soldats.charger()
        self.assertEqual([registre[i]['batailles'] for i in ids], [0, 1, 1, 1, 0, 0])
        self.assertEqual(registre[ids[3]]['blessures'], 1)
        self.assertTrue(registre[ids[0]]['detruit'])
        self.assertEqual(self.progression.charger(), progression)
        # Le reçu commun interdit le double gain pour la même bataille.
        with self.soldats.bataille_complete('lot-b:territoire'):
            with self.soldats.participation_temporaire([self.contribution(b)]) as groupe:
                groupe.participer([ids[3]])
        self.assertEqual(self.soldats.charger(), registre)

    def test_preparation_sans_engagement_ne_donne_aucune_experience(self):
        a = self.troupe('j1', 'piquier')
        avant = self.photo()
        with self.soldats.bataille_complete('preparation'):
            with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
                ids = [p.identifiant for p in groupe.participants]
                groupe.bloc(ids)
        self.assertEqual(self.photo(), avant)
        with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
            with self.assertRaisesRegex(RuntimeError, 'hors bataille'):
                groupe.participer(ids)
            with self.assertRaises(ValueError):
                groupe.participer(None)

    def test_interruption_bataille_ne_compte_pas_xp_et_libere_les_prets(self):
        a = self.troupe('j1', 'piquier', 2)
        with self.assertRaisesRegex(RuntimeError, 'interruption'):
            with self.soldats.bataille_complete('interrompue'):
                with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
                    ids = [p.identifiant for p in groupe.participants]
                    groupe.participer(ids)
                    groupe.appliquer_pertes(ids[:1], 0, moral=0)
                    raise RuntimeError('interruption')
        self.assertTrue(all(v['batailles'] == 0 for v in self.soldats.charger().values()))
        self.assertEqual(self.soldats._prets.get(), set())
        self.assertEqual(len(self.infos(a)['unites']), 1)

    def test_changement_de_contexte_meme_racine_refuse(self):
        a = self.troupe('j1', 'piquier', 1)
        with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
            with self.config.racines_generation(self.config.game_path, {}):
                with self.assertRaisesRegex(RuntimeError, 'hors génération'):
                    groupe.bilan()
            self.assertEqual(groupe.bloc()['nombre'], 1)

    def test_quatre_ordres_prepares_restent_hors_catalogue_executable(self):
        import ordres_conception
        noms = {'gros_poisson', 'muraille_humaine', 'ralliement', 'derniere_charge'}
        actifs = {o['nom'] for o in self.combats.catalogues.ORDRES.values() if o['disponible']}
        self.assertFalse(noms & actifs)
        self.assertTrue(all(not ordres_conception.ORDRES_EN_CONCEPTION[n]['disponible'] for n in noms))

    def test_source_etrangere_bloc_incorrect_et_general_falsifie_refuses(self):
        a, b = self.deux_generaux()
        ua, ub = self.infos(a)['unites'], self.infos(b)['unites']
        for contribution in ((a, 'avant', ub), (a, 'absent', ua),
                             (dict(a, joueur='j2'), 'avant', ua),
                             (dict(a, nom='general99'), 'avant', ua)):
            with self.assertRaises(ValueError):
                with self.soldats.participation_temporaire([contribution]):
                    self.fail('Source invalide acceptée.')

    def test_soldat_non_enregistre_non_cree_implicitement(self):
        a = self.troupe('j1', 'piquier')
        self.soldats.sauvegarder({})
        avant = self.photo()
        with self.assertRaisesRegex(RuntimeError, 'non authentifié'):
            with self.soldats.participation_temporaire([self.contribution(a)]):
                self.fail('Un soldat non enregistré a été créé implicitement.')
        self.assertEqual(self.photo(), avant)

    def test_copies_publiques_falsifiees_ne_modifient_pas_etat_prive(self):
        a = self.troupe('j1', 'piquier', 1)
        unite = self.infos(a)['unites'][0]
        identifiant = self.soldats.marqueur(unite)
        (unite / 'identifiant_soldat.txt').write_text('invente')
        (unite / 'blessures.txt').write_text('0')
        registre = self.soldats.charger()
        registre[identifiant]['blessures'] = 1
        self.soldats.sauvegarder(registre)
        with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
            self.assertEqual(groupe.participants[0].identifiant, identifiant)
            self.soldats.pertes(groupe.bloc(), 0, 100, random.Random(1))
            self.assertEqual(groupe.bloc()['nombre'], 0)

    def test_disparition_non_enregistree_et_remplacement_signales(self):
        a = self.troupe('j1', 'piquier', 1)
        unite = self.infos(a)['unites'][0]
        with self.soldats.participation_temporaire([self.contribution(a)]) as groupe:
            copie = unite.with_name('original_conserve')
            unite.rename(copie)
            with self.assertRaises(RuntimeError):
                groupe.bilan()
            shutil.copytree(copie, unite)
            with self.assertRaisesRegex(RuntimeError, 'Identité ou type'):
                groupe.bilan()

    def test_liens_symboliques_hardlinks_et_fifo_refuses(self):
        a = self.troupe('j1', 'piquier', 1)
        unite = self.infos(a)['unites'][0]
        lien = unite / 'lien'
        cible = unite / 'pique'
        for creer in (lambda: lien.symlink_to(cible),
                      lambda: os.link(cible, lien), lambda: os.mkfifo(lien)):
            creer()
            try:
                with self.assertRaises(RuntimeError):
                    with self.soldats.participation_temporaire([self.contribution(a)]):
                        self.fail('Un objet lié ou spécial a été accepté.')
            finally:
                lien.unlink()

    def test_generation_privee_utilise_uuid_captures_et_refuse_chemins_publics(self):
        a = self.troupe('j1', 'piquier', 2)
        publique = self.config.game_path
        privee = self.racine / 'copie_privee'
        shutil.copytree(publique, privee)
        prive = dict(a, chemin=privee / a['chemin'].relative_to(publique))
        ids = {self.soldats.marqueur(u) for u in self.infos(a)['unites']}
        with self.soldats.participation_temporaire([self.contribution(a)]) as ancien:
            with self.config.racines_generation(privee, {}):
                with self.assertRaisesRegex(RuntimeError, 'hors génération'):
                    ancien.bilan()
                with self.assertRaises(ValueError):
                    with self.soldats.participation_temporaire([self.contribution(a)]):
                        self.fail('Chemin public utilisé sous génération privée.')
        with self.config.racines_generation(privee, {}):
            with self.soldats.participation_temporaire([self.contribution(prive)]) as groupe:
                self.assertEqual({p.identifiant for p in groupe.participants}, ids)
                self.soldats.pertes(groupe.bloc(), 0, aleatoire=random.Random(1))
                self.assertEqual(groupe.bloc()['nombre'], 0)
        self.assertEqual(len(self.infos(a)['unites']), 2)

    def test_copie_uuid_privee_a_une_autre_origine_refusee(self):
        a, b = self.deux_generaux()
        racine = self.config.game_path
        # Simulation de la frontière privée déjà capturée ; aucune vraie partie.
        origine = self.infos(a)['unites'][0]
        copie = b['chemin'] / 'avant/infanterie99'
        shutil.copytree(origine, copie)
        with self.config.racines_generation(racine, {}):
            with self.assertRaisesRegex(RuntimeError, 'non authentifié'):
                with self.soldats.participation_temporaire([(b, 'avant', [copie])]):
                    self.fail('Une copie a récupéré l’identité de son original.')

    def preparer_publication(self):
        a = self.troupe('j1', 'piquier', 3)
        b = self.troupe('j2', 'piquier', 3, place='2')
        for g in (a, b):
            (g['chemin'] / 'ordre.txt').write_text('')
        self.activer(0)
        self.rapports.preparer_rapports(self.profil)
        return a, b

    def intervention_privee(self, a, b, interrompre=False):
        origine = self.survie._resoudre_tour_capture
        def resoudre(profil, aleatoire):
            resultat = origine(profil, aleatoire)
            copies = [dict(g, chemin=self.config.racine_metier() /
                           g['chemin'].relative_to(self.config.game_path)) for g in (a, b)]
            with self.soldats.participation_temporaire([self.contribution(g) for g in copies]) as groupe:
                groupe.appliquer_pertes([groupe.participants[0].identifiant], 0,
                                        moral=0, aleatoire=random.Random(1))
                groupe.appliquer_pertes([groupe.participants[-1].identifiant], 0,
                                        moral=100, aleatoire=random.Random(1))
                self.rapports.ecrire_rapport_court('Scénario technique : une perte, un blessé.')
                self.assertTrue(all(len(self.infos(g)['unites']) == 3 for g in (a, b)))
                if interrompre:
                    raise RuntimeError('interruption participation privée')
            return resultat
        return resoudre

    def test_publication_conserve_pertes_blessures_origines_et_rapport(self):
        a, b = self.preparer_publication()
        ids_a = {self.soldats.marqueur(u) for u in self.infos(a)['unites']}
        ids_b = {self.soldats.marqueur(u) for u in self.infos(b)['unites']}
        with patch.object(self.survie, '_resoudre_tour_capture',
                          side_effect=self.intervention_privee(a, b)), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, random.Random(1))
        apres_a = {self.soldats.marqueur(u) for u in self.infos(a)['unites']}
        apres_b = {self.soldats.marqueur(u) for u in self.infos(b)['unites']}
        self.assertEqual(len(apres_a), 2)
        self.assertTrue(apres_a < ids_a)
        self.assertEqual(apres_b, ids_b)
        registre = self.soldats.charger()
        self.assertEqual(sum(registre[i]['blessures'] for i in ids_b), 1)
        self.assertTrue(registre[next(iter(ids_a - apres_a))]['detruit'])
        self.assertIn('une perte, un blessé', self.config.rapport_court_path.read_text())
        # Le prochain inventaire reconnaît les nouveaux inodes publiés.
        self.soldats.synchroniser(self.profil)
        self.assertEqual(set(self.soldats.charger()), ids_a | ids_b)

    def test_interruption_privee_plateau_intact_reprise_sans_rejeu(self):
        a, b = self.preparer_publication()
        avant = copy.deepcopy(self.soldats.charger())
        rapports = {p: p.read_bytes() for p in self.config.rapport_dir.rglob('*') if p.is_file()}
        with patch.object(self.survie, '_resoudre_tour_capture',
                          side_effect=self.intervention_privee(a, b, interrompre=True)), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'interruption participation privée'):
                self.survie.resoudre_tour_survie(self.profil, random.Random(1))
        self.assertEqual(self.soldats.charger(), avant)
        self.assertEqual({p: p.read_bytes() for p in rapports}, rapports)
        self.assertEqual(self.soldats._prets.get(), set())
        self.assertEqual([len(self.infos(g)['unites']) for g in (a, b)], [3, 3])
        with patch.object(self.survie, '_resoudre_tour_capture') as calcul:
            with self.assertRaises(RuntimeError):
                self.survie.resoudre_tour_survie(self.profil, random.Random(1))
            calcul.assert_not_called()


class PreparationMuraille(unittest.TestCase):
    def test_exclusions_qg_et_reserve_sans_confondre_les_proprietaires(self):
        identites = [('j1', 'general1'), ('j2', 'general1'), ('j1', 'general2'), ('j2', 'general2')]
        self.assertEqual(ordres_calculs_v2.participants_muraille(identites,
            qg_nommade=('j1', 'general1'), reserve_strategique=('j2', 'general2')),
            (('j2', 'general1'), ('j1', 'general2')))
        self.assertEqual(ordres_calculs_v2.participants_muraille(reversed(identites)), tuple(reversed(identites)))

    def test_role_absent_ne_choisit_pas_de_remplacant_et_doublon_refuse(self):
        identites = [('j1', 'general1')]
        self.assertEqual(ordres_calculs_v2.participants_muraille(identites,
            qg_nommade=('j1', 'general99')), tuple(identites))
        with self.assertRaises(ValueError):
            ordres_calculs_v2.participants_muraille(identites * 2)
