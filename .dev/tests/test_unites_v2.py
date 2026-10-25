"""Unités V2 : règles, ressources et recettes sur parties temporaires isolées."""
import importlib
import os
import shutil
import unittest
from unittest.mock import Mock, patch

import test_soldats_formation
import test_crypte
CHMOD_REEL = os.chmod


class UnitesV2(unittest.TestCase):
    activer = test_soldats_formation.SoldatsFormation.activer
    general = test_soldats_formation.SoldatsFormation.general
    creer = test_soldats_formation.SoldatsFormation.creer
    infos = test_soldats_formation.SoldatsFormation.infos
    modules = test_soldats_formation.SoldatsFormation.modules

    def setUp(self):
        test_soldats_formation.SoldatsFormation.setUp(self)
        self.modules()
        self.unites = importlib.import_module('unites')
        self.morgue = importlib.import_module('morgue')

    def speciale(self, general, type_unite, numero=1, bloc='avant'):
        definition = self.unites.definition(type_unite)
        chemin = general['chemin'] / bloc / (definition['prefixe'] + str(numero))
        identifiant = self.unites.creer_officielle(chemin, type_unite, {'scenario': True})
        return chemin, identifiant

    def test_catalogue_valeurs_positions_et_soutien_zero(self):
        valeurs = {'sauvageon': (3, 3), 'chevalier_clinquant': (6, 5),
                   'orc_assaillant': (7, 6), 'orc_archer': (6, 6), 'orc_chaman': (2, 2),
                   'messager_du_QG': (0, 0), 'zombie': (5, 5), 'Trop_gros_zombie': (250, 250)}
        for nom, attendu in valeurs.items():
            infos = dict(type=nom, nombre=1)
            self.assertEqual(tuple(self.combats.valeur_base_bloc(infos, b)
                                   for b in ('avant', 'arriere')), attendu)
        self.assertFalse(self.unites.etiquette('orc_chaman', 'distance'))

    def test_faiblesses_distance_validee_et_non_magie(self):
        self.assertEqual(self.combats.multiplicateur('orc_archer', 'piquier'), 2)
        self.assertEqual(self.combats.multiplicateur('orc_chaman', 'piquier'), 1)
        definition = self.unites.definition('sauvageon')
        with patch.dict(definition, etiquettes=(*definition['etiquettes'], 'distance')):
            self.assertEqual(self.combats.multiplicateur('sauvageon', 'piquier'), 2)
        self.assertEqual(self.combats.multiplicateur('orc_chaman', 'orc_assaillant'), 3)
        self.assertEqual(self.combats.multiplicateur('orc_chaman', 'orc_archer'), 3)
        self.assertEqual(self.combats.multiplicateur('cavalerie_lourde', 'cavalier'), 2)
        for type_unite in self.combats.catalogues.UNITE_PAR_NOM:
            self.assertGreaterEqual(self.combats.multiplicateur(type_unite, 'zombie'), 2)

    def test_orcs_comptes_sur_armee_sans_cumuler_blocs(self):
        fiche = dict(points_commandement=20, moral=4)
        petits = dict(avant={'orc_assaillant': 3}, droite={'orc_archer': 2}, gauche={'orc_chaman': 2})
        self.assertEqual(self.unites.caracteristiques_armee(fiche, petits), dict(points_commandement=20, moral=1))
        grands = dict(avant={'orc_assaillant': 5}, droite={'orc_archer': 5}, gauche={'orc_chaman': 5},
                      arriere={'chevalier_clinquant': 2})
        self.assertEqual(self.unites.caracteristiques_armee(fiche, grands), dict(points_commandement=20, moral=11))
        self.assertEqual(fiche, dict(points_commandement=20, moral=4))
        self.assertEqual(self.unites.caracteristiques_armee(fiche, {'avant': {'archer': 4}}), fiche)

    def test_gros_zombie_dix_places_et_aucune_perte_adverse(self):
        self.assertEqual(self.unites.occupation({'avant': {'Trop_gros_zombie': 1},
                                                'arriere': {'zombie': 10}}), 20)
        self.assertEqual(self.combats.combat_bloc(dict(type='Trop_gros_zombie', nombre=1),
                                                 dict(type='archer', nombre=5)), (1, 5))

    def test_non_combattant_ne_cause_aucun_degat_ni_division_zero(self):
        a, b = dict(type='messager_du_QG', nombre=10), dict(type='archer', nombre=1)
        self.assertEqual(self.combats.combat_bloc(a, b), (0, 1))
        self.assertEqual(self.combats.combat_bloc(b, a), (1, 0))
        self.assertEqual(self.unites.ordres_messagers(3, 2, True), 2)
        self.assertEqual(self.unites.ordres_messagers(3, 2, False), 0)

    def test_zombie_blessures_anciennes_conservees_sans_nouveau_sauvetage(self):
        g = self.creer(nombre=0)
        chemin, identifiant = self.speciale(g, 'zombie')
        registre = self.soldats.charger()
        registre[identifiant].update(batailles=10, blessures=2)
        self.soldats.sauvegarder(registre)
        self.assertEqual(len(self.combats.supprimer_unites(self.infos(g), 0, g)), 1)
        self.assertEqual(self.soldats.charger()[identifiant]['blessures'], 2)
        self.assertFalse(chemin.exists())

    def test_soins_interdits_aux_orcs_et_deux_tours_chevalier(self):
        g = self.creer(nombre=0)
        _, chevalier = self.speciale(g, 'chevalier_clinquant')
        _, orc = self.speciale(g, 'orc_archer', bloc='arriere')
        registre = self.soldats.charger()
        for valeur in registre.values():
            valeur.update(blessures=1, batailles=8)
        self.soldats.sauvegarder(registre)
        presences = {chevalier: [1, 2, 3], orc: [4, 5, 6]}
        for tour in (1, 2):
            self.formation.commencer_sejour(tour, g, 'hopital', 'allies', [7, 8, 9], unites=presences)
            self.assertTrue(self.formation.valider_sejour(tour, g, 'hopital', 'allies', [7, 8, 9], True, presences))
            self.assertFalse(self.formation.valider_sejour(tour, g, 'hopital', 'allies', [7, 8, 9], True, presences))
            self.assertEqual(self.soldats.charger()[chevalier]['blessures'], 1 if tour == 1 else 0)
            self.assertEqual(self.soldats.charger()[orc]['blessures'], 1)
        self.assertEqual(self.soldats.charger()[chevalier]['batailles'], 8)

    def test_sejour_chevalier_interrompu_ne_cumule_pas(self):
        g = self.creer(nombre=0)
        _, identifiant = self.speciale(g, 'chevalier_clinquant')
        registre = self.soldats.charger()
        registre[identifiant]['blessures'] = 1
        self.soldats.sauvegarder(registre)
        presence = {identifiant: [1, 2, 3]}
        for tour in (1, 3):
            self.formation.commencer_sejour(tour, g, 'hopital', 'allies', [7], unites=presence)
            self.formation.valider_sejour(tour, g, 'hopital', 'allies', [7], True, presence)
        self.assertEqual(self.soldats.charger()[identifiant]['blessures'], 1)

    def test_propager_arrondi_survie_et_rejeu(self):
        g = self.creer(nombre=0)
        for pertes in range(1, 7):
            attendu = (pertes + 1) // 2
            self.assertEqual(self.unites.propager(g, 'arriere', pertes, 1, str(pertes), 'duel'), attendu)
            self.assertEqual(self.unites.propager(g, 'arriere', pertes, 1, str(pertes), 'duel'), 0)
        self.assertEqual(self.unites.propager(g, 'arriere', 20, 0, 'mort', 'duel'), 0)
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 12)

    def test_propagation_depassement_illimite_puis_trim_sans_historique(self):
        g = self.creer(nombre=0)
        _, ancien = self.speciale(g, 'zombie')
        self.unites.propager(g, 'arriere', 40, 1, 'choc', 'duel')
        self.unites.propager(g, 'arriere', 100, 1, 'manoeuvre', 'duel')
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 71)
        self.assertEqual(self.unites.terminer_duel(g, 'duel'), 51)
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 20)
        self.assertFalse(self.soldats.charger()[ancien].get('detruit'))
        self.assertEqual(self.unites.terminer_duel(g, 'duel'), 0)

    def test_propagation_interrompue_ne_cree_pas_deux_fois(self):
        g = self.creer(nombre=0)
        with patch.object(self.soldats, 'publier', side_effect=RuntimeError('panne')):
            with self.assertRaisesRegex(RuntimeError, 'panne'):
                self.unites.propager(g, 'arriere', 4, 1, 'evenement', 'duel')
        nombre = len(list((g['chemin'] / 'arriere').iterdir()))
        with self.assertRaisesRegex(RuntimeError, 'sans rejeu'):
            self.unites.propager(g, 'arriere', 4, 1, 'evenement', 'duel')
        self.assertEqual(len(list((g['chemin'] / 'arriere').iterdir())), nombre)

    def reanimer(self):
        self.profil.update(probabilite_general_zombie=1, acces_morgue='premiere_apparition')
        g = self.creer(nombre=0, territoire='village')
        self.etat.sauvegarder_compteur_general('j1', 1)
        self.assertTrue(self.morgue.enregistrer_mort(self.profil, g, 'bataille', Mock(random=lambda: 0)))
        self.generaux.supprimer_general_si_vide(g)
        self.morgue.materialiser(self.profil)
        return dict(joueur='j1', nom='general2', chemin=self.morgue.zone(self.profil, 'j1') / 'generaux/general2')

    def test_mort_sans_probabilite_ne_tire_ni_ne_reanime(self):
        g = self.creer(nombre=0)
        self.profil['probabilite_general_zombie'] = None
        hasard = Mock()
        self.assertFalse(self.morgue.enregistrer_mort(self.profil, g, 'bataille', hasard))
        hasard.random.assert_not_called()
        self.assertEqual(self.morgue.charger(self.profil)['cadavres'], {})

    def test_zombification_cadavre_uniques_historique_et_ordres(self):
        g = self.reanimer()
        avant = self.morgue.charger(self.profil)
        hasard = Mock()
        ancien = dict(joueur='j1', nom='general1')
        self.assertTrue(self.morgue.enregistrer_mort(self.profil, ancien, 'reprise', hasard))
        self.morgue.materialiser(self.profil)
        hasard.random.assert_not_called()
        self.assertEqual(self.morgue.charger(self.profil), avant)
        self.assertEqual(len(avant['cadavres']), 1)
        self.assertTrue(self.progression.charger()['j1:general1']['mort'])
        self.assertTrue(self.morgue.est_zombie(g))
        g['ordres'] = [{'identifiant': '1-2'}]
        self.assertFalse(self.generaux.general_possede_ordre(g, '1-2'))
        self.assertNotIn('j1:general1', self.etat.charger_positions_generaux())

    def rituel(self, g):
        identifiant = next(iter(self.morgue.charger(self.profil)['cadavres']))
        source = self.morgue.zone(self.profil, 'j1') / 'cadavres' / ('cadavre_' + identifiant)
        dossier = self.morgue.zone(self.profil, 'j1') / 'rituels' / g['nom'] / 'avant' / identifiant
        (dossier / 'reliques').mkdir(parents=True)
        (dossier / 'rituel').mkdir()
        os.link(source, dossier / 'reliques/coeur_necrotique')
        (dossier / 'rituel/ame').symlink_to('../reliques/coeur_necrotique')
        return identifiant, source, dossier

    def test_rituel_vrais_inodes_lien_relatif_et_consommation_unique(self):
        g = self.reanimer()
        identifiant, source, dossier = self.rituel(g)
        preuve = self.morgue.authentifier_rituel(self.profil, 'j1', g, 'avant', identifiant, dossier)
        self.assertTrue(self.morgue.consommer_rituel(self.profil, preuve, g))
        self.assertFalse(self.morgue.consommer_rituel(self.profil, preuve, g))
        self.assertFalse(source.exists())
        self.assertEqual(self.generaux.lire_composition_general(g['chemin'])['avant'], {'Trop_gros_zombie': 1})

    def test_rituel_copie_et_lien_absolu_refuses(self):
        g = self.reanimer()
        identifiant, source, dossier = self.rituel(g)
        ame = dossier / 'rituel/ame'
        ame.unlink()
        ame.symlink_to(dossier / 'reliques/coeur_necrotique')
        with self.assertRaisesRegex(ValueError, 'relatif'):
            self.morgue.authentifier_rituel(self.profil, 'j1', g, 'avant', identifiant, dossier)
        ame.unlink()
        ame.symlink_to('../reliques/coeur_necrotique')
        lien = dossier / 'reliques/coeur_necrotique'
        lien.unlink()
        shutil.copyfile(source, lien)
        with self.assertRaisesRegex(ValueError, 'physique'):
            self.morgue.authentifier_rituel(self.profil, 'j1', g, 'avant', identifiant, dossier)

    def test_zombie_mv_valide_conserve_identite_blessures_et_experience(self):
        g = self.reanimer()
        origine = self.creer(numero=3, territoire='village', place='2')
        self.soldats.synchroniser(self.profil)
        unite = self.infos(origine)['unites'][0]
        identifiant = self.soldats.marqueur(unite)
        registre = self.soldats.charger()
        registre[identifiant].update(batailles=8, blessures=2)
        self.soldats.sauvegarder(registre)
        self.securite.memoriser_unites_actions(self.profil, 1)
        unite.rename(g['chemin'] / 'avant' / unite.name)
        reference = self.etat.charger_unites_actions(self.profil)
        reference['capture'] = self.securite.inventorier_unites_actions(self.profil)
        self.etat.sauvegarder_unites_actions(self.profil, reference)
        self.assertEqual(self.morgue.convertir_deplacements(self.profil), 1)
        self.assertEqual(self.morgue.convertir_deplacements(self.profil), 0)
        valeur = self.soldats.charger()[identifiant]
        self.assertEqual((valeur['type'], valeur['blessures'], valeur['batailles']), ('zombie', 2, 8))
        self.assertEqual(len(self.morgue.charger(self.profil)['cadavres']), 1)

    def test_chevalier_transformation_tour_complet_identite_et_blessures(self):
        g = self.creer(nombre=0, territoire='village', place='ecole_officiers/1')
        chemin, identifiant = self.speciale(g, 'sauvageon')
        registre = self.soldats.charger()
        registre[identifiant].update(blessures=3, batailles=10)
        self.soldats.sauvegarder(registre)
        fiches = self.progression.charger()
        fiches['j1:general1']['evolutions_acquises'].append(106)
        self.progression.sauvegarder(fiches)
        (chemin / 'sauvageon.txt').unlink()
        general = dict(g, lieu='ecole_officiers')
        unites = self.formation.relever_unites(general)
        self.formation.commencer_sejour(1, g, 'ecole_officiers', 'allies', [1], unites=unites)
        self.assertFalse(self.formation.valider_sejour(1, g, 'ecole_officiers', 'allies', [1], False, unites))
        self.assertEqual(self.soldats.charger()[identifiant]['type'], 'sauvageon')
        self.assertTrue(self.formation.valider_sejour(1, g, 'ecole_officiers', 'allies', [1], True, unites))
        valeur = self.soldats.charger()[identifiant]
        self.assertEqual((valeur['type'], valeur['blessures'], valeur['batailles']), ('chevalier_clinquant', 3, 10))
        nouveau = self.infos(g)['unites'][0]
        self.assertEqual(self.soldats.marqueur(nouveau), identifiant)
        self.assertFalse(self.formation.valider_sejour(1, g, 'ecole_officiers', 'allies', [1], True, unites))

    def test_messager_permissions_recrutement_et_copie_frauduleuse(self):
        g = self.creer(nombre=0, territoire='home', nature='stratege')
        fiches = self.progression.charger()
        fiches['j1:general1']['evolutions_acquises'].append(110)
        self.progression.sauvegarder(fiches)
        chemin = g['chemin'] / 'avant/messager_du_QG1'
        chemin.mkdir()
        for nom, mode in (('monocle', 0o600), ('sceau du roi', 0o060), ('enveloppe', 0o006)):
            (chemin / nom).touch()
            CHMOD_REEL(chemin / nom, mode)
        self.assertTrue(self.unites.permissions_messager(chemin))
        CHMOD_REEL(chemin / 'monocle', 0o660)
        self.assertFalse(self.unites.permissions_messager(chemin))
        CHMOD_REEL(chemin / 'monocle', 0o600)
        self.unites.scanner_messagers(self.profil)
        identifiant = self.soldats.marqueur(chemin)
        self.assertTrue(self.soldats.charger()[identifiant]['origine_officielle'])
        self.unites.scanner_messagers(self.profil)
        self.assertEqual(self.soldats.marqueur(chemin), identifiant)
        for nom in ('monocle', 'sceau du roi', 'enveloppe'):
            CHMOD_REEL(chemin / nom, 0o600)
        copie = chemin.with_name('messager_du_QG2')
        shutil.copytree(chemin, copie)
        self.soldats.synchroniser(self.profil)
        self.securite.auditer_unites_speciales(self.profil)
        self.assertTrue(chemin.exists())
        self.assertFalse(copie.exists())

    def test_construction_manuelle_zombie_sans_conversion_refusee(self):
        g = self.creer(nombre=0, territoire='home')
        faux = g['chemin'] / 'avant/zombi1'
        faux.mkdir()
        self.securite.auditer_unites_speciales(self.profil)
        self.assertFalse(faux.exists())

    def test_rituel_ne_permet_pas_copie_ni_liens_hors_zone_capture(self):
        g = self.reanimer()
        identifiant, source, dossier = self.rituel(g)
        self.morgue.relever_rituels(self.profil, 1)
        self.assertEqual(len(self.morgue.charger(self.profil)['rituels']['preuves']), 1)
        copie = self.racine / 'morgue-copie'
        self.cycle_linux.copier(self.morgue.zone(self.profil, 'j1'), copie,
                               exercices=(self.morgue.zone(self.profil, 'j1') / 'rituels',))
        self.assertFalse((copie / 'rituels').exists())
        self.assertTrue((copie / 'cadavres' / source.name).exists())
        hors_zone = g['chemin'] / 'avant/zombi_faux'
        hors_zone.symlink_to(dossier / 'rituel', target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'Lien interdit'):
            self.cycle_linux.copier(g['chemin'], self.racine / 'copie-refusee')

    def test_mort_declenchee_par_resolution_reelle(self):
        g = self.creer(nombre=0)
        self.profil['probabilite_general_zombie'] = 1
        with self.soldats.bataille_complete('mort-reelle', self.profil):
            self.generaux.supprimer_general_si_vide(g)
        mort = self.morgue.charger(self.profil)['morts']['j1:general1']
        self.assertTrue(mort['zombifie'])
        self.assertEqual(mort['bataille'], 'mort-reelle')

    def test_messager_coexiste_sans_degats_et_meurt_avec_bloc(self):
        g = self.creer(nombre=2, nature='stratege')
        chemin, identifiant = self.speciale(g, 'messager_du_QG')
        infos = self.infos(g)
        self.assertEqual((infos['type'], infos['nombre'], len(infos['soutiens'])), ('archer', 2, 1))
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 3)
        self.combats.supprimer_unites(infos, 1, g)
        self.assertTrue(chemin.exists())
        self.combats.supprimer_unites(infos, 0, g)
        self.assertFalse(chemin.exists())
        self.assertTrue(self.soldats.charger()[identifiant]['detruit'])

    def test_messager_ne_permet_pas_melange_combattant(self):
        g = self.creer(nombre=1)
        self.speciale(g, 'messager_du_QG')
        unite = g['chemin'] / 'avant/cavalerie1'
        unite.mkdir()
        (unite / 'cheval').touch()
        self.assertEqual(self.infos(g)['nombre'], 0)
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 0)

    def test_chaman_moral_proportionnel_sans_mutation_et_fraction_exacte(self):
        from fractions import Fraction
        fiche = dict(points_commandement=20, moral=50)
        composition = dict(avant={'sauvageon': 5}, droite={'orc_chaman': 1})
        self.assertEqual(self.unites.moral_bloc(fiche, composition, 'avant'), Fraction(2091, 50))
        composition['droite']['orc_chaman'] = 2
        self.assertEqual(self.unites.moral_bloc(fiche, composition, 'avant'), Fraction(1092, 25))
        self.assertEqual(self.unites.moral_bloc(fiche, composition, 'avant'), Fraction(1092, 25))
        self.assertEqual(fiche['moral'], 50)
        fiche['moral'] = 11
        self.assertEqual(self.unites.moral_bloc(fiche, composition, 'avant'), Fraction(78, 25))
        self.assertEqual(self.unites.moral_bloc(fiche, composition, 'droite'), 3)

    def test_chaman_soins_territoire_allies_uniquement_et_rejeu(self):
        g = self.creer(nombre=0, territoire='est_1')
        _, chaman = self.speciale(g, 'orc_chaman')
        allie = self.creer(numero=2, territoire='est_1', place='2')
        absent = self.creer(numero=3, territoire='est_2')
        for general in (allie, absent):
            self.combats.supprimer_unites(self.infos(general), 0, general)
        registre = self.soldats.charger()
        registre[chaman]['blessures'] = 1
        self.soldats.sauvegarder(registre)
        ici = self.soldats.marqueur(self.infos(allie)['unites'][0])
        ailleurs = self.soldats.marqueur(self.infos(absent)['unites'][0])
        self.unites.soigner_victoire_territoriale(self.profil, self.config.game_path / 'est_1', 'victoire')
        registre = self.soldats.charger()
        self.assertEqual((registre[chaman]['blessures'], registre[ici]['blessures'], registre[ailleurs]['blessures']), (0, 0, 1))
        registre[ici]['blessures'] = 1
        self.soldats.sauvegarder(registre)
        self.unites.soigner_victoire_territoriale(self.profil, self.config.game_path / 'est_1', 'victoire')
        self.assertEqual(self.soldats.charger()[ici]['blessures'], 1)

    def test_regeneration_fuite_restaure_effectif_initial_et_identites(self):
        g = self.creer(nombre=0)
        identifiants = {self.speciale(g, 'sauvageon', n)[1] for n in range(12)}
        self.unites.memoriser_sauvageons([g], 'duel-sauvageon')
        self.combats.supprimer_unites(self.infos(g), 5, g)
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 5)
        self.assertEqual(self.unites.regenerer_fuite(g, self.profil), 7)
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 12)
        self.assertEqual({self.soldats.marqueur(u) for u in self.infos(g)['unites']}, identifiants)
        self.assertEqual(self.unites.regenerer_fuite(g, self.profil), 0)

    def test_zombie_niveau_sans_recompense_et_tirage_uniforme_unites(self):
        g = self.creer(nombre=0)
        fiche = self.progression.caracteristiques_general(g)
        fiche['etat_zombie'] = True
        apres, recompense = self.progression.monter_niveau(fiche, Mock())
        self.assertIsNone(recompense)
        self.assertEqual(apres['niveau'], fiche['niveau'] + 1)
        self.assertEqual(apres['niveaux_zombie'], 1)
        self.assertEqual(self.progression.capacite_maximale(apres), 22)
        self.assertEqual(apres['evolutions_acquises'], fiche['evolutions_acquises'])
        fiche.pop('etat_zombie')
        catalogue = {105: dict(categorie='unite', disponible=True, natures=None),
                     108: dict(categorie='unite', disponible=True, natures=None)}
        for index, attendu in enumerate((105, 108)):
            rng = Mock(randint=Mock(side_effect=[1, index]))
            apres, recompense = self.progression.monter_niveau(fiche, rng, catalogue)
            self.assertEqual(recompense, attendu)
            self.assertEqual(apres['evolutions_acquises'], [attendu])
            self.assertEqual(rng.randint.call_args.args, (0, 1))


    def test_spore_transforme_le_moins_experimente_et_garde_identite(self):
        bouclier = importlib.import_module('bouclier_vivant')
        zombie = self.creer(nombre=0)
        self.speciale(zombie, 'zombie', bloc='arriere')
        chemin = self.general('bot', numero=1, territoire='est_3',
                              nombre=2, equipement='pique')
        ennemi = dict(joueur='bot', nom=chemin.name, chemin=chemin)
        registre = self.soldats.charger()
        candidats = sorted((chemin / 'avant').iterdir())
        ids = []
        for i, dossier in enumerate(candidats):
            identifiant = self.soldats.enregistrer(dossier, registre, 'piquier')
            registre[identifiant]['batailles'] = 8 if i == 0 else 1
            self.soldats.publier(dossier, identifiant, registre[identifiant])
            ids.append(identifiant)
        self.soldats.sauvegarder(registre)
        choix = bouclier.convertir_spore(zombie, ennemi, 'avant', 'spore:test')
        self.assertEqual(choix, ids[1])
        resultat = self.soldats.charger()[choix]
        self.assertEqual((resultat['type'], resultat['batailles']), ('zombie', 1))
        self.assertEqual(self.generaux.lire_composition_general(zombie['chemin'])['arriere'],
                         {'zombie': 2})
        self.assertEqual(self.generaux.lire_composition_general(chemin)['avant'],
                         {'piquier': 1})
        self.assertIsNone(bouclier.convertir_spore(zombie, ennemi, 'avant', 'spore:test'))

    def test_bouclier_intervient_avant_choc_et_spore_agit(self):
        zombie = self.creer(nombre=0)
        self.speciale(zombie, 'Trop_gros_zombie', bloc='avant')
        for n in range(1, 11):
            self.speciale(zombie, 'zombie', n, bloc='arriere')
        chemin = self.general('bot', numero=1, territoire='est_3',
                              nombre=3, equipement='pique')
        ennemi = dict(joueur='bot', nom=chemin.name, chemin=chemin)
        registre = self.soldats.charger()
        for dossier in (chemin / 'avant').iterdir():
            identifiant = self.soldats.enregistrer(dossier, registre, 'piquier')
            self.soldats.publier(dossier, identifiant, registre[identifiant])
        self.soldats.sauvegarder(registre)
        with self.soldats.bataille_complete('survie:0:est_3', self.profil):
            resultat = self.combats.combat_entre_generaux(zombie, ennemi)
        self.assertTrue(resultat['chocs'])
        self.assertEqual(resultat['chocs'][0]['type_1'], 'Trop_gros_zombie')
        self.assertIn('spores', self.unites.charger_capacites())

    def test_resistance_reste_entre_duels_d_un_territoire(self):
        bouclier = importlib.import_module('bouclier_vivant')
        zombie = self.creer(nombre=0)
        with self.soldats.bataille_complete('survie:9:est_3', self.profil):
            bouclier._sauver_resistance(zombie, 212.5)
            self.assertEqual(bouclier._lire_resistance(zombie), 212.5)
        self.assertEqual(bouclier._lire_resistance(zombie), 250)



class CryptePlaines(unittest.TestCase):
    gestion = test_crypte.Crypte.gestion
    general = test_crypte.Crypte.general
    activer = test_crypte.Crypte.activer

    def setUp(self):
        test_crypte.Crypte.setUp(self)
        self.plaines = self.crypte.contexte_plaines(self.profil)
        chemin = self.general(territoire='est_1', place='crypte_des_plaines/1', nombre=0)
        self.beneficiaire = dict(joueur='j1', nom=chemin.name, chemin=chemin)
        self.progression = importlib.import_module('progression')
        fiches = self.progression.charger()
        fiches['j1:general1']['evolutions_acquises'] = [105, 107, 108, 109]
        self.progression.sauvegarder(fiches)

    def message(self, op, **champs):
        if op == 'start':
            self.seq['j1'] = 0
        else:
            self.seq['j1'] += 1
        message = dict(event=op, seq=self.seq['j1'], token=self.tokens.get('j1'),
                       cwd=str(self.crypte.zone(self.plaines, 'j1') / 'atelier'), **champs)
        resultat = self.collecteur.evenement(1001, (123, 'session'), message)
        if op == 'start':
            self.tokens['j1'] = resultat
        return resultat

    def executer(self, recette, numero=2):
        self.message('start')
        atelier = self.crypte.zone(self.plaines, 'j1') / 'atelier'
        lignes = self.crypte.catalogue(self.plaines)[recette]['lignes']
        for modele in lignes:
            ligne = modele.replace('{ligne}', f'echo {numero} > ligne.txt').replace('{bloc}', 'echo gauche > bloc.txt')
            kind = 'builtin' if ligne == 'pwd' or ligne.startswith('echo ') else 'file'
            self.message('before', line=ligne, command=ligne, kind=kind, history='1/1')
            if ligne.startswith('cp '):
                (atelier / f'tome_du_{recette}').write_text(self.crypte.LIVRES[recette], encoding='utf-8')
            elif modele == '{ligne}':
                (atelier / 'ligne.txt').write_text(str(numero) + '\n')
            elif modele == '{bloc}':
                (atelier / 'bloc.txt').write_text('gauche\n')
            elif ligne == 'mkdir sauvageon':
                (atelier / 'sauvageon').mkdir()
            elif ligne.startswith('vi '):
                (atelier / 'sauvageon/sauvageon.txt').write_text('boueux\net\ncrasseux\n')
            self.message('after', status='0')

    def test_bibliotheque_stable_et_occurrences_nombreuses(self):
        dossier = self.config.game_path / 'village/j1/hotel_de_ville/bibliotheque'
        avant = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in dossier.iterdir()}
        self.crypte.preparer(self.profil)
        self.assertEqual(avant, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in dossier.iterdir()})
        self.assertGreaterEqual(len(self.crypte.lignes_orc_archer()), 6)

    def test_catalogues_distincts_et_pdf_nouvelles_recettes(self):
        self.assertFalse(set(self.crypte.catalogue(self.profil)) & set(self.crypte.catalogue(self.plaines)))
        self.assertEqual(len(list((self.crypte.zone(self.plaines, 'j1') / 'grimoire').glob('*.pdf'))), 4)
        self.message('start')
        erreur = self.message('before', line='mkdir appel', command='mkdir appel', kind='file', history='1/1')
        self.assertIn('inattendue', erreur)

    def test_toutes_lignes_orc_archer_acceptees_par_collecteur(self):
        for numero in sorted(self.crypte.lignes_orc_archer()):
            self.executer('orc_archer', numero)
            self.message('end')
            d = self.crypte.charger(self.plaines)
            self.assertEqual(d['j1']['a_creer']['bloc'], 'gauche')
            d['j1'].update(dernier_tour=None, a_creer=None)
            self.crypte.sauver(self.plaines, d)

    def test_ligne_non_correspondante_et_fichiers_sans_commandes_refuses(self):
        self.executer('orc_archer', 1)
        with self.assertRaises(ValueError):
            self.message('end')
        self.message('start')
        atelier = self.crypte.zone(self.plaines, 'j1') / 'atelier'
        (atelier / 'tome_du_orc_archer').write_text(self.crypte.LIVRES['orc_archer'])
        (atelier / 'ligne.txt').write_text('2\n')
        (atelier / 'bloc.txt').write_text('avant\n')
        with self.assertRaisesRegex(ValueError, 'incomplète'):
            self.message('end')

    def test_recettes_assailant_chaman_sauvageon_et_rejeu(self):
        for recette in ('orc_assaillant', 'orc_chaman', 'sauvageon'):
            self.executer(recette)
            self.message('end')
            with self.assertRaisesRegex(ValueError, 'rejoué'):
                self.message('end')
            d = self.crypte.charger(self.plaines)
            self.assertEqual(d['j1']['a_creer']['recette'], recette)
            d['j1'].update(dernier_tour=None, a_creer=None)
            self.crypte.sauver(self.plaines, d)

    def test_connaissance_absente_ne_consomme_pas_recompense(self):
        fiches = self.progression.charger()
        fiches['j1:general1']['evolutions_acquises'] = []
        self.progression.sauvegarder(fiches)
        self.executer('orc_archer')
        with self.assertRaisesRegex(ValueError, 'personnellement'):
            self.message('end')
        self.assertIsNone(self.crypte.charger(self.plaines)['j1']['dernier_tour'])

    def test_connaissance_autre_general_et_fiche_falsifiee_ne_debloquent_pas(self):
        autre = self.general(numero=2, territoire='village', place='2', nombre=0)
        fiches = self.progression.charger()
        fiches['j1:general1']['evolutions_acquises'] = []
        fiches['j1:general2']['evolutions_acquises'] = [108]
        self.progression.sauvegarder(fiches)
        with (self.beneficiaire['chemin'] / 'fiche.txt').open('a') as fichier:
            fichier.write('\nevolutions_acquises=108\n')
        with self.assertRaisesRegex(ValueError, 'personnellement'):
            self.crypte.verifier_connaissance_plaines(self.plaines, 'j1', 108)
        self.assertTrue(autre.exists())

    def test_livraison_quatre_unites_au_general_existant_et_rejeu(self):
        self.executer('orc_archer')
        self.message('end')
        compteur = self.etat.lire_compteur_general('j1')
        self.crypte.materialiser(self.plaines, 3)
        composition = self.generaux.lire_composition_general(self.beneficiaire['chemin'])
        self.assertEqual(composition['gauche'], {'orc_archer': 4})
        self.crypte.materialiser(self.plaines, 3)
        self.assertEqual(self.generaux.lire_composition_general(self.beneficiaire['chemin']), composition)
        self.assertEqual(self.etat.lire_compteur_general('j1'), compteur)

    def test_livraison_capacite_et_bloc_de_remplacement(self):
        g = self.beneficiaire['chemin']
        for i in range(18):
            unite = g / 'gauche' / f'infanterie{i}'
            unite.mkdir()
            (unite / 'arc').touch()
        self.executer('orc_archer')
        self.message('end')
        with patch.object(self.crypte.random_livraison, 'choice', return_value='droite'):
            self.crypte.materialiser(self.plaines, 3)
        self.assertEqual(self.generaux.lire_composition_general(g)['droite'], {'orc_archer': 2})
        self.assertEqual(self.generaux.total_general_depuis_chemin(g), 20)

    def test_aucune_place_aucune_creation(self):
        g = self.beneficiaire['chemin']
        for i in range(20):
            unite = g / 'avant' / f'infanterie{i}'
            unite.mkdir()
            (unite / 'arc').touch()
        self.executer('orc_chaman')
        self.message('end')
        self.crypte.materialiser(self.plaines, 3)
        self.assertEqual(self.generaux.total_general_depuis_chemin(g), 20)
        self.assertEqual(self.crypte.charger(self.plaines)['j1']['attributions'][0]['nombre'], 0)
