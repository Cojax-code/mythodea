"""Hybrides, bâtiments partagés et Forge sur un plateau temporaire isolé."""
import importlib
import shutil
import unittest
from unittest.mock import Mock, patch

import test_soldats_formation
from support_cycle import GelSimule


class ComplementsMoteur(unittest.TestCase):
    setUp = test_soldats_formation.SoldatsFormation.setUp
    activer = test_soldats_formation.SoldatsFormation.activer
    general = test_soldats_formation.SoldatsFormation.general
    modules = test_soldats_formation.SoldatsFormation.modules
    creer = test_soldats_formation.SoldatsFormation.creer
    infos = test_soldats_formation.SoldatsFormation.infos

    def forge(self, nature='instinctif', technologie=True, complet=True, nombre=1):
        general = self.creer(nature=nature, territoire='village', place='forge/1',
                             equipement='cheval', nombre=nombre)
        profils = self.progression.charger()
        profils['j1:general1']['evolutions_acquises'] = [104] if technologie else []
        self.progression.sauvegarder(profils)
        for unite in (general['chemin'] / 'avant').iterdir():
            for nom in ('cuirasse', 'armure', 'casque', 'bouclier') if complet else ('cuirasse',):
                (unite / nom).touch()
        return general

    def terminer(self, tour=1):
        self.formation.clore_tour(self.profil, tour)
        self.formation.resoudre_tour(self.profil, tour)

    def test_probabilites_exactes_quatre_natures_et_traits(self):
        self.modules()
        obtenus = dict.fromkeys(self.progression.NATURES, 0)
        for tirage in range(1, 101):
            fiche = self.progression.nouvelles_caracteristiques(Mock(randint=Mock(side_effect=[tirage, 51, 1])))
            obtenus[fiche['nature']] += 1
            self.assertEqual(fiche['trait_inne'], 'leader')
            self.assertEqual(fiche['orientation_principale'], fiche['nature'].removesuffix('_hybride'))
        self.assertEqual(obtenus, dict(stratege=45, instinctif=45, stratege_hybride=5, instinctif_hybride=5))

    def test_apprentissages_croises_et_gains_sans_changement_nature_trait(self):
        self.modules()
        for nature, evolution in (('stratege_hybride', 202), ('instinctif_hybride', 201)):
            fiche = self.progression.nouvelles_caracteristiques()
            fiche.update(nature=nature, niveau=4, moral=0, evolution_apprise=evolution)
            apres, identifiant = self.progression.monter_niveau(fiche, Mock(randint=lambda a, b: b))
            self.assertEqual((identifiant, apres['niveau'], apres['nature'], apres['trait_inne']),
                             (evolution, 5, nature, fiche['trait_inne']))
            self.assertEqual(apres['moral'], 6 if evolution == 202 else 0)
            self.assertEqual(apres['points_commandement'] - fiche['points_commandement'],
                             40 if evolution == 201 else 0)
            # Les apprentissages croisés n'entrent jamais dans le tirage ordinaire.
            self.assertNotIn(evolution, self.progression.evolutions_eligibles(fiche, apprentissage=False))

    def test_qg_hybride_et_ordres_seulement_si_acquis(self):
        commandement = importlib.import_module('commandement')
        qg = dict(nature='instinctif_hybride', points_commandement=20, qg='avant', effectif_bloc_qg=1)
        self.assertIs(commandement.selectionner_qg([qg], lambda g: g['points_commandement']), qg)
        self.assertEqual(commandement.ordres_applicables([1002], qg['nature'], 'globale', 1), [])
        self.assertEqual(commandement.ordres_applicables([1002], qg['nature'], 'globale', 1, acquis=[1002]), [1002])
        qg['nature'] = 'instinctif'
        self.assertIs(commandement.selectionner_qg([qg], lambda g: 20), qg)
        self.assertEqual(commandement.ordres_applicables(
            [1002], qg['nature'], 'globale', 1, acquis=[1002]), [])

    def test_moral_stratege_hybride_reel(self):
        general = self.creer(nature='stratege_hybride')
        profils = self.progression.charger()
        profils['j1:general1']['moral'] = 100
        self.progression.sauvegarder(profils)
        self.assertEqual(self.combats.supprimer_unites(self.infos(general), 0, general), [])

    def test_home_passage_village_obligatoire_et_aucune_marche_forcee(self):
        mouvements = importlib.import_module('mouvements')
        for destination, attendu in (('village', (True, False)), ('est_1', (False, False)), ('est_2', (False, False)),
                                      ('est_3', (False, False))):
            self.assertEqual(mouvements.verifier_deplacement_general(
                'j1', 'home', destination, {}, self.profil)[:2], attendu)
        self.assertEqual(mouvements.verifier_deplacement_general('j1', 'village', 'est_2', {}, self.profil)[:2],
                         (True, True))
        zero = dict(self.profil, tour_preparation=True)
        self.assertFalse(mouvements.verifier_deplacement_general('j1', 'home', 'est_1', {}, zero)[0])
        source = self.general(territoire='home', nombre=1)
        cible = self.config.game_path / 'village/forge/1/j1/general1'
        source.rename(cible)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'village')
        self.assertNotIn('j1:general1', self.etat.charger_generaux_fatigues())

    def test_nouvelle_creation_ne_contourne_pas_home(self):
        source = self.general(territoire='home', nombre=0)
        self.securite.memoriser_unites_actions(self.profil, 1, creations=['j1:general1'])
        unite = source / 'avant/cavalerie1'
        unite.mkdir()
        (unite / 'cheval').touch()
        cible = self.config.game_path / 'est_2/j1/1/general1'
        source.rename(cible)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertNotEqual(self.etat.charger_positions_generaux()['j1:general1'], 'est_2')
        self.assertNotIn('j1:general1', self.etat.charger_generaux_fatigues())

    def test_recompense_deplacement_immediat_et_pas_de_droit_persistant(self):
        crypte = self.survie.crypte
        crypte.preparer(self.profil)
        donnees = crypte.charger(self.profil)
        nom = crypte.attribuer_recompense(self.profil, 'j1', donnees['j1'], {'id': 'test', 'tour': 1},
                                         crypte.RECETTES['recette1'])
        crypte.sauver(self.profil, donnees)
        self.securite.memoriser_unites_actions(self.profil, 1)
        source = self.config.game_path / 'village/j1/crypte/recompense' / nom
        cible = self.config.game_path / 'est_1/j1/1' / nom
        source.rename(cible)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(self.etat.charger_positions_generaux()[f'j1:{nom}'], 'est_1')
        self.securite.memoriser_unites_actions(self.profil, 2)
        # Le tour suivant utilise la position actuelle ; une marche de deux cases fatigue.
        cible.rename(self.config.game_path / 'est_3/j1/1' / nom)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertIn(f'j1:{nom}', self.etat.charger_generaux_fatigues())

    def test_forge_cycle_publication_et_scan_suivant_conservent_soldat(self):
        general = self.forge(nature='instinctif_hybride')
        unite = general['chemin'] / 'avant/cavalerie1'
        for n in range(10):
            self.soldats.terminer_bataille([unite], str(n))
        registre = self.soldats.charger()
        identifiant = self.soldats.marqueur(unite)
        registre[identifiant]['blessures'] = 2
        self.soldats.sauvegarder(registre)
        self.formation.ouvrir_tour(self.profil, 1)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        gestion.preparer()
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        lourde = general['chemin'] / 'avant/cavalerie_L1'
        self.assertTrue(lourde.is_dir())
        self.assertFalse(unite.exists())
        self.assertEqual(self.soldats.marqueur(lourde), identifiant)
        self.assertEqual((self.soldats.charger()[identifiant]['blessures'],
                          self.soldats.charger()[identifiant]['batailles']), (2, 10))
        self.assertTrue((lourde / 'heroique').exists())
        self.assertIn('Forge', self.config.rapport_court_path.read_text())
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertTrue(lourde.is_dir())
        self.assertEqual(self.generaux.identifier_unite(lourde), 'cavalerie_lourde')

    def test_forge_recette_incomplete_preserve_unite(self):
        general = self.forge(complet=False)
        self.formation.ouvrir_tour(self.profil, 1)
        self.terminer()
        self.assertTrue((general['chemin'] / 'avant/cavalerie1/cheval').exists())
        self.assertFalse(list(general['chemin'].rglob('cavalerie_L*')))

    def test_forge_sans_technologie_et_strateges_refuses(self):
        general = self.forge(technologie=False)
        for tour, nature, acquis in ((1, 'instinctif', []), (2, 'stratege', [104]),
                                      (3, 'stratege_hybride', [104])):
            profils = self.progression.charger()
            profils['j1:general1'].update(nature=nature, evolutions_acquises=acquis)
            self.progression.sauvegarder(profils)
            self.formation.ouvrir_tour(self.profil, tour)
            self.terminer(tour)
            self.assertTrue((general['chemin'] / 'avant/cavalerie1').is_dir())

    def test_forge_sejour_incomplet_et_recette_tardive_refuses(self):
        general = self.forge(complet=False)
        self.formation.ouvrir_tour(self.profil, 1)
        for nom in ('armure', 'casque', 'bouclier'):
            (general['chemin'] / 'avant/cavalerie1' / nom).touch()
        self.terminer()
        self.assertFalse(list(general['chemin'].rglob('cavalerie_L*')))
        self.formation.ouvrir_tour(self.profil, 2)
        ailleurs = self.config.game_path / 'village/j1/reserve/general1'
        general['chemin'].rename(ailleurs)
        ailleurs.rename(general['chemin'])
        self.terminer(2)
        self.assertFalse(list(general['chemin'].rglob('cavalerie_L*')))

    def test_forge_collision_noms_et_pas_de_transformation_repetee(self):
        general = self.forge()
        (general['chemin'] / 'avant/cavalerie_L1').mkdir()
        self.formation.ouvrir_tour(self.profil, 1)
        self.terminer()
        self.assertTrue((general['chemin'] / 'avant/cavalerie_L2').is_dir())
        avant = self.soldats.charger()
        self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual(self.soldats.charger(), avant)

    def test_six_places_physiques_ecole_et_forge_unique(self):
        ecole = self.config.game_path / 'village/ecole_officiers'
        self.assertEqual(sorted(p.name for p in ecole.iterdir() if p.is_dir()), list('123456'))
        self.assertFalse((self.config.game_path / 'village/j1/ecole_officiers').exists())
        general = self.forge()
        self.general(joueur='j2', territoire='village', place='forge/1', equipement='cheval')
        self.assertFalse([g for g in self.formation.occupants(self.profil) if g['lieu'] == 'forge'])
        self.assertEqual(self.securite.securiser_emplacements_generaux(self.profil),
                         {'j1:general1', 'j2:general1'})
        self.assertFalse(general['chemin'].exists())

    def test_migration_ecole_ancienne_preserve_identite_et_fichiers(self):
        general = self.creer(territoire='village', place='ecole_officiers/1')
        ancien = self.config.game_path / 'village/j1/ecole_officiers/1/general1'
        ancien.parent.mkdir(parents=True)
        inode = general['chemin'].stat().st_ino
        general['chemin'].rename(ancien)
        self.formation.preparer_emplacements(self.profil)
        self.assertEqual(general['chemin'].stat().st_ino, inode)
        self.assertFalse(ancien.parent.exists())
        self.assertTrue((general['chemin'] / 'ordre.txt').exists())

    def test_migration_documents_restants_ne_reinitialisent_pas_sejour(self):
        general = self.creer(territoire='village', place='hopital/1')
        ancien = self.config.game_path / 'village/j1/ecole_officiers'
        ancien.mkdir(parents=True)
        (ancien / 'notes.txt').write_text('notes personnelles')
        self.formation.ouvrir_tour(self.profil, 1)
        preuve = self.formation.preuve_general(general)
        self.formation.migrer_ancienne_ecole(self.profil)
        self.assertEqual(self.formation.preuve_general(general), preuve)
        self.assertTrue((ancien / 'notes.txt').exists())

    def test_nouveaux_generaux_acces_village_et_batiments_apres_creation_unites(self):
        destinations = ('j1/reserve', 'j1/garnison/1', 'j1/hopital/1',
                        'ecole_officiers/1/j1', 'forge/1/j1')
        for numero, relatif in enumerate(destinations, 1):
            source = self.general(numero=numero, territoire='home', nombre=0)
            identite = f'j1:general{numero}'
            self.securite.memoriser_unites_actions(self.profil, 1, [identite], creations=[identite])
            unite = source / 'avant/cavalerie1'
            unite.mkdir()
            (unite / 'cheval').touch()
            cible = self.config.game_path / 'village' / relatif / source.name
            source.rename(cible)
            self.securite.verifier_tous_les_deplacements(self.profil)
            self.assertEqual(self.etat.charger_positions_generaux()[identite], 'village')
            self.assertTrue((cible / 'avant/cavalerie1/cheval').exists())
            self.assertNotIn(identite, self.etat.charger_generaux_fatigues())

    def test_recompense_immediate_ne_saute_pas_distance_autorisee(self):
        crypte = self.survie.crypte
        crypte.preparer(self.profil)
        donnees = crypte.charger(self.profil)
        nom = crypte.attribuer_recompense(self.profil, 'j1', donnees['j1'], {'id': 'test', 'tour': 1},
                                         crypte.RECETTES['recette1'])
        crypte.sauver(self.profil, donnees)
        self.securite.memoriser_unites_actions(self.profil, 1)
        source = self.config.game_path / 'village/j1/crypte/recompense' / nom
        source.rename(self.config.game_path / 'est_3/j1/1' / nom)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(self.etat.charger_positions_generaux()[f'j1:{nom}'], 'repli')

    def test_effacer_fichier_blessures_ne_guerit_pas(self):
        general = self.creer()
        self.combats.supprimer_unites(self.infos(general), 0, general)
        unite = self.infos(general)['unites'][0]
        (unite / 'blessures.txt').unlink()
        self.soldats.synchroniser(self.profil)
        self.assertEqual((unite / 'blessures.txt').read_text(), '1\n')

    def test_lectures_croisees_simultanees_avant_remplacement(self):
        self.modules()
        eleves = [self.creer(numero=n, nature='instinctif_hybride', territoire='village',
                            place=f'ecole_officiers/{n}') for n in (1, 2)]
        professeur = self.creer(numero=3, nature='instinctif', territoire='village', place='ecole_officiers/3')
        profils = self.progression.charger()
        profils['j1:general3']['evolutions_acquises'] = [202]
        self.progression.sauvegarder(profils)
        donnees = self.formation.charger()
        donnees['manuels']['allies'] = {'001': 1002, '002': None, '003': None}
        self.formation.sauvegarder(donnees)
        self.formation.preparer(self.profil)
        for general in eleves:
            (general['chemin'] / 'lire_les_memoires.txt').write_text('A 001 1002')
        (professeur['chemin'] / 'ecrire_ses_memoires.txt').write_text('E 001 202')
        self.formation.ouvrir_tour(self.profil, 1)
        self.terminer()
        self.assertEqual(self.formation.charger()['manuels']['allies']['001'], 202)
        for general in eleves:
            fiche = self.progression.caracteristiques_general(general)
            self.assertEqual(fiche['evolution_apprise'], 1002)
            self.assertNotIn(1002, fiche['evolutions_acquises'])
            self.assertEqual(self.progression.attribuer_niveau(general), 1002)
            self.assertIn(1002, self.progression.caracteristiques_general(general)['evolutions_acquises'])

    def test_forge_partielle_ne_supprime_aucun_cavalier_et_copie_non_autorisee(self):
        general = self.forge(nombre=2)
        (general['chemin'] / 'avant/cavalerie2/casque').unlink()
        self.formation.ouvrir_tour(self.profil, 1)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        gestion.preparer()
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        lourde = general['chemin'] / 'avant/cavalerie_L1'
        legere = general['chemin'] / 'avant/cavalerie2'
        self.assertTrue(lourde.is_dir())
        self.assertTrue(legere.is_dir())
        copie = general['chemin'] / 'avant/cavalerie_L9'
        shutil.copytree(lourde, copie)
        self.soldats.synchroniser(self.profil)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertFalse(copie.exists())
        self.assertTrue(lourde.exists())
        self.assertTrue(legere.exists())

    def test_fuite_reserve_conserve_soldat_blesse_heroique_et_profil(self):
        general = self.creer(territoire='est_1', nombre=1)
        unite = self.infos(general)['unites'][0]
        for n in range(10):
            self.soldats.terminer_bataille([unite], str(n))
        self.combats.supprimer_unites(self.infos(general), 0, general)
        for n in range(1, 5):
            self.general(joueur='j2', numero=n, territoire='village', place=str(n), nombre=1)
        self.creer(numero=2, territoire='village', place='hopital/1')
        profil = self.progression.caracteristiques_general(general)
        fichiers = {p.relative_to(general['chemin']): p.read_bytes()
                    for p in general['chemin'].rglob('*') if p.is_file()}
        mouvements = importlib.import_module('mouvements')
        general['emplacement'] = '1'
        destination = mouvements.retraite_surnombre(general, self.config.game_path / 'est_1', self.profil)
        self.assertEqual(destination, self.config.game_path / 'village/j1/reserve/general1')
        self.assertEqual({p.relative_to(destination): p.read_bytes()
                          for p in destination.rglob('*') if p.is_file()}, fichiers)
        self.assertEqual(self.progression.caracteristiques_general(general), profil)


if __name__ == '__main__':
    unittest.main()
