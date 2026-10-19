"""Blessures, soins et mémoires sur le plateau temporaire du moteur."""
import importlib
import shutil
import unittest
from unittest.mock import Mock, patch

import test_cycle_survie


class SoldatsFormation(unittest.TestCase):
    setUp = test_cycle_survie.CycleSurvie.setUp
    activer = test_cycle_survie.CycleSurvie.activer
    general = test_cycle_survie.CycleSurvie.general

    def modules(self):
        self.soldats = importlib.import_module('soldats')
        self.progression = importlib.import_module('progression')
        self.formation = importlib.import_module('formation')

    def creer(self, numero=1, nombre=1, nature='instinctif', **position):
        self.modules()
        chemin = self.general(numero=numero, nombre=nombre, **position)
        general = dict(joueur='j1', nom=chemin.name, chemin=chemin)
        registre = self.progression.charger()
        registre[f'j1:{chemin.name}'].update(nature=nature, moral=100 if nature == 'instinctif' else 0)
        self.progression.sauvegarder(registre)
        return general

    def infos(self, general):
        return self.generaux.lire_blocs_general(general['chemin'])['avant']

    def test_sauvetage_moral_reel_avant_affrontement_suivant(self):
        general = self.creer(nombre=2)
        infos = self.infos(general)
        self.assertEqual(self.combats.supprimer_unites(infos, 0, general), [])
        self.assertEqual(infos['nombre'], 2)
        self.assertEqual([int((u / 'blessures.txt').read_text()) for u in infos['unites']], [1, 1])
        # Les unités sauvées restent disponibles mais ne peuvent pas dépasser leur limite.
        self.assertEqual(len(self.combats.supprimer_unites(infos, 0, general)), 2)
        self.assertEqual(infos['nombre'], 0)

    def test_tentative_sur_blesse_ne_se_reporte_pas(self):
        general = self.creer(nombre=2)
        infos = self.infos(general)
        rng = Mock(sample=lambda population, n: list(population)[:n])
        premiere = dict(nombre=1, type='archer', unites=[infos['unites'][0]])
        self.soldats.pertes(premiere, 0, 100, rng)
        self.assertEqual(len(self.soldats.pertes(infos, 0, 50, rng)), 2)

    def test_limites_statuts_et_une_seule_bataille_complete(self):
        general = self.creer()
        unite = self.infos(general)['unites'][0]
        for bataille in range(10):
            self.soldats.terminer_bataille([unite, unite], f'bataille-{bataille}')
            self.soldats.terminer_bataille([unite], f'bataille-{bataille}')
        self.soldats.terminer_bataille([unite], 'bataille-0')
        self.assertEqual((unite / 'batailles_survecues.txt').read_text(), '10\n')
        self.assertTrue((unite / 'veteran').is_file())
        self.assertTrue((unite / 'heroique').is_file())
        self.assertEqual([self.soldats.limite_blessures(n) for n in (0, 4, 5, 9, 10)], [1, 1, 2, 2, 3])
        for _ in range(3):
            self.assertEqual(self.combats.supprimer_unites(self.infos(general), 0, general), [])
        self.assertEqual(len(self.combats.supprimer_unites(self.infos(general), 0, general)), 1)

    def test_modification_manuelle_ne_guerit_pas_et_transfert_suit_dossier(self):
        general = self.creer()
        unite = self.infos(general)['unites'][0]
        self.combats.supprimer_unites(self.infos(general), 0, general)
        (unite / 'blessures.txt').write_text('0')
        autre = self.creer(numero=2, nombre=0)
        destination = autre['chemin'] / 'avant/infanterie7'
        shutil.move(str(unite), str(destination))
        self.soldats.synchroniser(self.profil)
        self.assertEqual((destination / 'blessures.txt').read_text(), '1\n')
        self.assertEqual(len(self.combats.supprimer_unites(self.infos(autre), 0, autre)), 1)

    def test_fiche_morale_modifiee_ne_change_pas_moral_officiel(self):
        general = self.creer(nature='stratege')
        with (general['chemin'] / 'fiche.txt').open('a') as f:
            f.write('\nnature=instinctif\nmoral=100\n')
        self.assertEqual(len(self.combats.supprimer_unites(self.infos(general), 0, general)), 1)

    def test_soin_valide_un_tour_entier_et_conserve_statuts(self):
        general = self.creer()
        unite = self.infos(general)['unites'][0]
        for n in range(10):
            self.soldats.terminer_bataille([unite], str(n))
        self.combats.supprimer_unites(self.infos(general), 0, general)
        identifiant = self.soldats.marqueur(unite)
        presence = {identifiant: [11, 12, 13]}
        self.formation.commencer_sejour(1, general, 'hopital', 'allies', [1, 2, 3], unites=presence)
        self.assertFalse(self.formation.valider_sejour(1, general, 'hopital', 'allies', [1, 2, 3]))
        self.assertEqual(self.soldats.charger()[identifiant]['blessures'], 1)
        self.assertFalse(self.formation.valider_sejour(1, general, 'hopital', 'allies', [1, 2, 3], True))
        self.assertTrue(self.formation.valider_sejour(1, general, 'hopital', 'allies', [1, 2, 3], True,
                                                    unites=presence))
        self.soldats.synchroniser(self.profil)
        self.assertEqual((unite / 'blessures.txt').read_text(), '0\n')
        self.assertEqual((unite / 'batailles_survecues.txt').read_text(), '10\n')
        self.assertTrue((unite / 'heroique').exists())
        # La répétition d'une validation ne soigne pas une blessure ultérieure.
        self.combats.supprimer_unites(self.infos(general), 0, general)
        self.assertFalse(self.formation.valider_sejour(1, general, 'hopital', 'allies', [1, 2, 3], True))
        self.assertEqual(self.soldats.charger()[identifiant]['blessures'], 1)

    def enseignant(self):
        general = self.creer(nature='stratege')
        registre = self.progression.charger()
        registre['j1:general1']['evolutions_acquises'] = [201]
        self.progression.sauvegarder(registre)
        return general

    def test_ecole_demandes_figees_et_tour_complet(self):
        general = self.enseignant()
        self.formation.commencer_sejour(1, general, 'ecole_officiers', 'allies', [1], ecrire='001 201')
        self.assertFalse(self.formation.commencer_sejour(1, general, 'ecole_officiers', 'allies',
                                                        [1], ecrire='002 201'))
        self.assertFalse(self.formation.valider_sejour(1, general, 'ecole_officiers', 'allies', [1]))
        self.assertTrue(self.formation.valider_sejour(1, general, 'ecole_officiers', 'allies', [1], True))
        self.assertEqual(self.formation.charger()['manuels']['allies'], {'001': 201, '002': None, '003': None})
        self.formation.commencer_sejour(2, general, 'ecole_officiers', 'allies', [1], ecrire='003 201')
        self.assertFalse(self.formation.valider_sejour(2, general, 'ecole_officiers', 'allies', [2], True))
        self.assertIsNone(self.formation.charger()['manuels']['allies']['003'])

    def test_memoire_apprise_id_reel_independant_du_manuel_et_recompense_garantie(self):
        professeur = self.enseignant()
        self.formation.commencer_sejour(1, professeur, 'ecole_officiers', 'allies', [1], ecrire='001 201')
        self.formation.valider_sejour(1, professeur, 'ecole_officiers', 'allies', [1], True)
        eleve = self.creer(numero=2, nature='stratege')
        self.formation.commencer_sejour(2, eleve, 'ecole_officiers', 'allies', [2], lire='001')
        self.formation.valider_sejour(2, eleve, 'ecole_officiers', 'allies', [2], True)
        registre = self.formation.charger()
        self.assertEqual(registre['manuels']['allies']['001'], 201)
        registre['manuels']['allies']['001'] = 202
        self.formation.sauvegarder(registre)
        self.assertEqual(self.progression.caracteristiques_general(eleve)['evolution_apprise'], 201)
        self.assertEqual(self.progression.attribuer_niveau(eleve, Mock(randint=lambda a, b: a)), 201)
        self.assertIsNone(self.progression.caracteristiques_general(eleve)['evolution_apprise'])

    def test_emplacements_valides_et_autorisation_ecriture(self):
        general = self.creer(nature='stratege')
        for texte in ('004 201', '001 9999', '001', '001 201 extra'):
            with self.assertRaises(ValueError):
                self.formation.demande_ecriture(texte)
        with self.assertRaises(ValueError):
            self.formation.commencer_sejour(1, general, 'ecole_officiers', 'allies', [1], ecrire='001 201')

    def test_hopital_unite_sortie_non_soignee(self):
        general = self.creer()
        unite = self.infos(general)['unites'][0]
        self.combats.supprimer_unites(self.infos(general), 0, general)
        identifiant = self.soldats.marqueur(unite)
        self.formation.commencer_sejour(1, general, 'hopital', 'allies', [1], unites={identifiant: [12]})
        self.formation.valider_sejour(1, general, 'hopital', 'allies', [1], True, unites={identifiant: [13]})
        self.assertEqual(self.soldats.charger()[identifiant]['blessures'], 1)

    def test_remplacement_des_trois_emplacements(self):
        general = self.enseignant()
        registre = self.formation.charger()
        registre['manuels']['allies'] = dict.fromkeys(self.formation.EMPLACEMENTS, 202)
        self.formation.sauvegarder(registre)
        for tour, place in enumerate(self.formation.EMPLACEMENTS, 1):
            self.formation.commencer_sejour(tour, general, 'ecole_officiers', 'allies', [1],
                                            ecrire=f'{place} 201')
            self.formation.valider_sejour(tour, general, 'ecole_officiers', 'allies', [1], True)
        self.assertEqual(self.formation.charger()['manuels']['allies'],
                         dict.fromkeys(self.formation.EMPLACEMENTS, 201))

    def test_choc_et_rapport_comptent_survivants_sauves(self):
        general = self.creer(nombre=2)
        ennemi_path = self.general(joueur='bot', numero=1, nombre=2)
        ennemi = dict(joueur='bot', nom='general1', chemin=ennemi_path)
        armee = {'j1': self.generaux.lire_blocs_general(general['chemin']),
                 'bot': self.generaux.lire_blocs_general(ennemi_path)}
        with patch.object(self.combats, 'combat_bloc', return_value=(0, 0)):
            detail = self.combats.confrontation_directe(armee, general, ennemi, 'avant')
        self.assertEqual((detail['final_1'], detail['final_2']), (2, 0))
        self.assertEqual(len(armee['j1']['avant']['unites']), 2)

    def test_generation_publie_blessures_et_conserve_autorite(self):
        from support_cycle import GelSimule
        general = self.creer()
        unite = self.infos(general)['unites'][0]
        self.combats.supprimer_unites(self.infos(general), 0, general)
        identifiant = self.soldats.marqueur(unite)
        (unite / 'blessures.txt').write_text('0')
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        gestion.preparer()
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertEqual((unite / 'blessures.txt').read_text(), '1\n')
        self.assertEqual(self.soldats.marqueur(unite), identifiant)
        self.assertEqual(self.soldats.charger()[identifiant]['inode'], unite.stat().st_ino)
        self.assertEqual(self.progression.caracteristiques_general(general)['moral'], 100)

    def test_diagnostic_ordre_ne_publie_pas_contenu_prive(self):
        general = self.creer()
        secret = 'SECRET_personnel-ne-pas-publier'
        (general['chemin'] / 'ordre.txt').write_text(secret + '\n1-2\n999-999\n')
        with patch.object(self.generaux.rapports, 'afficher_et_ecrire') as rapport:
            ordres = self.generaux.lire_ordres_general(general['chemin'])
        self.assertEqual([o['identifiant'] for o in ordres], ['1-2'])
        self.assertNotIn(secret, str(rapport.call_args_list))
        self.assertNotIn('999-999', str(rapport.call_args_list))

    def test_scans_lectures_avant_ecritures_et_publication(self):
        from support_cycle import GelSimule
        professeur = self.creer(nature='stratege', territoire='village', place='ecole_officiers/1')
        eleve = self.creer(numero=2, territoire='village', place='ecole_officiers/2')
        profils = self.progression.charger()
        profils['j1:general1']['evolutions_acquises'] = [201]
        profils['j1:general2']['moral'] = 0
        self.progression.sauvegarder(profils)
        donnees = self.formation.charger()
        donnees['manuels']['allies'] = {'001': 202, '002': None, '003': None}
        self.formation.sauvegarder(donnees)
        self.formation.preparer(self.profil)
        (professeur['chemin'] / 'ecrire_ses_memoires.txt').write_text('E 001 201')
        (eleve['chemin'] / 'lire_les_memoires.txt').write_text('A 001 202')
        self.formation.ouvrir_tour(self.profil, 1)
        # Une réécriture pendant ACTIONS ne remplace pas la demande enregistrée.
        (eleve['chemin'] / 'lire_les_memoires.txt').write_text('a 003 201')
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        gestion.preparer()
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertEqual(self.progression.caracteristiques_general(eleve)['evolution_apprise'], 202)
        self.assertEqual(self.formation.charger()['manuels']['allies']['001'], 201)
        self.assertIn('001 201', (self.config.game_path / 'village/ecole_officiers/memoire_des_generaux.txt').read_text())

    def test_sejour_entree_tardive_et_sortie_retour_refuses(self):
        general = self.creer(territoire='village', place='hopital/1')
        unite = self.infos(general)['unites'][0]
        self.combats.supprimer_unites(self.infos(general), 0, general)
        self.formation.ouvrir_tour(self.profil, 1)
        ailleurs = general['chemin'].parents[1] / '2/general1'
        general['chemin'].rename(ailleurs)
        ailleurs.rename(general['chemin'])
        tardif = self.creer(numero=2, territoire='village', place='hopital/3')
        self.combats.supprimer_unites(self.infos(tardif), 0, tardif)
        self.formation.clore_tour(self.profil, 1)
        self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual(self.soldats.charger()[self.soldats.marqueur(unite)]['blessures'], 1)
        unite_tardive = self.infos(tardif)['unites'][0]
        self.assertEqual(self.soldats.charger()[self.soldats.marqueur(unite_tardive)]['blessures'], 1)

    def test_soins_simultanes_toutes_places_et_mouvement_interne_gratuit(self):
        generaux = [self.creer(numero=n, territoire='village', place=f'hopital/{n}') for n in range(1, 8)]
        for general in generaux:
            self.combats.supprimer_unites(self.infos(general), 0, general)
        self.formation.ouvrir_tour(self.profil, 1)
        self.formation.clore_tour(self.profil, 1)
        self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual({v['blessures'] for v in self.soldats.charger().values()}, {0})
        # Les bâtiments sont des sous-zones du village : aucun coût de mouvement.
        general = generaux[0]
        destination = self.config.game_path / 'village/ecole_officiers/1/j1/general1'
        general['chemin'].rename(destination)
        self.assertEqual(self.generaux.trouver_position_general('j1', 'general1', self.profil),
                         ('village', destination))
        mouvements = importlib.import_module('mouvements')
        self.assertEqual(mouvements.verifier_deplacement_general('j1', 'village', 'village', {}, self.profil),
                         (True, False, 'immobile'))
        self.assertEqual(len([z for z in self.generaux.zones_generaux('j1', self.profil)
                             if z.get('batiment') == 'ecole_officiers']), 6)

    def test_apprentissage_refuse_id_different_du_manuel(self):
        general = self.creer(nature='stratege')
        donnees = self.formation.charger()
        donnees['manuels']['allies'] = dict.fromkeys(self.formation.EMPLACEMENTS, 201)
        self.formation.sauvegarder(donnees)
        self.formation.commencer_sejour(1, general, 'ecole_officiers', 'allies', [1], lire='a 001 202')
        with self.assertRaisesRegex(ValueError, 'contenu du manuel'):
            self.formation.valider_sejour(1, general, 'ecole_officiers', 'allies', [1], True)

    def test_bataille_territoriale_comptee_une_fois_pour_plusieurs_duels(self):
        general = self.creer(nombre=20)
        ennemi_path = self.general(joueur='bot', numero=1, nombre=1, equipement='pique')
        ennemi = dict(joueur='bot', nom='general1', chemin=ennemi_path)
        with self.soldats.bataille_complete('survie:1:est_3'):
            self.combats.combat_entre_generaux(general, ennemi)
            autre_path = self.general(joueur='bot', numero=2, nombre=1, equipement='pique')
            self.combats.combat_entre_generaux(general, dict(joueur='bot', nom='general2', chemin=autre_path))
        for unite in self.infos(general)['unites']:
            self.assertEqual((unite / 'batailles_survecues.txt').read_text(), '1\n')

    def test_cycle_compte_bataille_et_exclut_general_non_engage(self):
        general = self.creer(nombre=20, territoire='village', nature='stratege')
        reserve = self.creer(numero=2, territoire='village', place='hopital/1')
        self.general(joueur='bot', numero=1, territoire='village', nombre=1, equipement='pique')
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie._resoudre_tour_capture(self.profil)
        unites = self.infos(general)['unites']
        self.assertTrue(unites)
        self.assertTrue(all((u / 'batailles_survecues.txt').read_text() == '1\n' for u in unites))
        self.assertFalse((self.infos(reserve)['unites'][0] / 'batailles_survecues.txt').exists())

    def test_places_ecole_partagees_et_distinctes_de_garnison(self):
        premier = self.creer(territoire='village', place='ecole_officiers/1')
        autre = self.general(joueur='j2', numero=1, territoire='village', place='ecole_officiers/1')
        garnison = self.creer(numero=2, territoire='village', place='1')
        punis = self.securite.securiser_emplacements_generaux(self.profil)
        self.assertEqual(punis, {'j1:general1', 'j2:general1'})
        self.assertFalse(premier['chemin'].exists())
        self.assertFalse(autre.exists())
        self.assertTrue(garnison['chemin'].exists())

    def test_ecritures_concurrentes_refusees_ensemble(self):
        for numero in (1, 2):
            general = self.creer(numero=numero, nature='stratege', territoire='village',
                                 place=f'ecole_officiers/{numero}')
            profils = self.progression.charger()
            profils[f'j1:general{numero}']['evolutions_acquises'] = [201]
            self.progression.sauvegarder(profils)
            self.formation.preparer_demandes(general)
            (general['chemin'] / 'ecrire_ses_memoires.txt').write_text('e 001 201')
        self.formation.ouvrir_tour(self.profil, 1)
        self.formation.clore_tour(self.profil, 1)
        self.formation.resoudre_tour(self.profil, 1)
        self.assertFalse(self.formation.charger()['manuels'])
        self.assertFalse(self.formation.charger()['sejours'])

    def test_ecriture_annulee_par_depart_ne_bloque_pas_ecriture_valide(self):
        for numero in (1, 2):
            general = self.creer(numero=numero, nature='stratege', territoire='village',
                                 place=f'ecole_officiers/{numero}')
            profils = self.progression.charger()
            profils[f'j1:general{numero}']['evolutions_acquises'] = [201]
            self.progression.sauvegarder(profils)
            self.formation.preparer_demandes(general)
            (general['chemin'] / 'ecrire_ses_memoires.txt').write_text('e 001 201')
        self.formation.ouvrir_tour(self.profil, 1)
        general['chemin'].rename(self.config.game_path / 'village/j1/reserve/general2')
        self.formation.clore_tour(self.profil, 1)
        self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual(self.formation.charger()['manuels']['allies']['001'], 201)


if __name__ == '__main__':
    unittest.main()
