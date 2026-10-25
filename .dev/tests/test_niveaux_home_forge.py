"""Progression attestée et ancienneté Forge sur des parties temporaires."""
import importlib
import shutil
import unittest
from unittest.mock import Mock, patch

import test_complements_moteur
from support_cycle import GelSimule


class NiveauxHomeForge(unittest.TestCase):
    setUp = test_complements_moteur.ComplementsMoteur.setUp
    activer = test_complements_moteur.ComplementsMoteur.activer
    general = test_complements_moteur.ComplementsMoteur.general
    creer = test_complements_moteur.ComplementsMoteur.creer
    modules = test_complements_moteur.ComplementsMoteur.modules
    infos = test_complements_moteur.ComplementsMoteur.infos
    forge = test_complements_moteur.ComplementsMoteur.forge
    terminer = test_complements_moteur.ComplementsMoteur.terminer

    def fiche(self, general):
        return self.progression.caracteristiques_general(general)

    def preparer_points(self, general, **champs):
        profils = self.progression.charger()
        profils[f"{general['joueur']}:{general['nom']}"].update(champs)
        self.progression.sauvegarder(profils)

    def adversaire(self, nombre=1):
        chemin = self.general(joueur='bot', nombre=nombre)
        return dict(joueur='bot', nom=chemin.name, chemin=chemin)

    def choc(self, general, ennemi, survivants=None):
        armee = {g['joueur']: self.generaux.lire_blocs_general(g['chemin']) for g in (general, ennemi)}
        if survivants is None:
            survivants = tuple(armee[g['joueur']]['avant']['nombre'] for g in (general, ennemi))
        with patch.object(self.combats, 'combat_bloc', return_value=survivants):
            return self.combats.confrontation_directe(armee, general, ennemi, 'avant')

    def test_deux_resolutions_recompense_garantie_et_plusieurs_blocs_un_point(self):
        general = self.creer(nature='stratege')
        ennemi = self.adversaire()
        self.preparer_points(general, evolution_apprise=201, progression_formation=2)
        avant = self.fiche(general)['points_commandement']
        with patch.object(self.progression, 'aleatoire_progression', Mock(randint=lambda a, b: a)):
            for tour in (1, 2):
                with self.soldats.bataille_complete(f'survie:{tour}:est_3', self.profil):
                    for _ in range(3):
                        self.choc(general, ennemi)
                    self.assertEqual(self.fiche(general)['niveau'], 0)
                self.assertEqual(self.fiche(general)['niveau'], tour // 2)
        fiche = self.fiche(general)
        self.assertEqual((fiche['progression_combat'], fiche['progression_formation']), (0, 2))
        self.assertEqual(fiche['points_commandement'], avant + 11)
        self.assertIsNone(fiche['evolution_apprise'])

    def test_defaite_survecue_et_destruction_tardive(self):
        general = self.creer(nombre=3, nature='stratege')
        ennemi = self.adversaire(nombre=4)
        with self.soldats.bataille_complete('defaite', self.profil):
            self.choc(general, ennemi, (1, 4))
        self.assertEqual(self.fiche(general)['progression_combat'], 1)
        with self.soldats.bataille_complete('mort-fin-territoire', self.profil):
            self.choc(general, ennemi)
            self.combats.supprimer_unites(self.infos(general), 0, general)
            self.generaux.supprimer_general_si_vide(general)
        self.assertEqual(self.fiche(general)['progression_combat'], 1)
        self.assertEqual(self.fiche(general)['niveau'], 0)

    def test_fuite_avant_ou_apres_affrontement(self):
        general = self.creer(nature='stratege')
        ennemi = self.adversaire()
        mouvements = importlib.import_module('mouvements')
        general['emplacement'] = '1'
        with self.soldats.bataille_complete('fuite-apres', self.profil):
            self.choc(general, ennemi)
            mouvements.retraite_surnombre(general, self.config.game_path / 'est_3', self.profil)
        self.assertEqual(self.fiche(general)['progression_combat'], 1)
        sans_combat = self.creer(numero=2, nature='stratege', place='2')
        sans_combat['emplacement'] = '2'
        with self.soldats.bataille_complete('fuite-avant', self.profil):
            # Une sélection pour un duel / un relevé des soldats ne suffit pas.
            self.soldats.participer(sans_combat)
            mouvements.retraite_surnombre(sans_combat, self.config.game_path / 'est_3', self.profil)
        self.assertEqual(self.fiche(sans_combat)['progression_combat'], 0)

    def test_cascade_reelle_comptabilisee_une_fois(self):
        general = self.creer(nombre=20, nature='stratege', ordre=2)
        for numero in range(1, 11):
            self.general(joueur='bot', numero=numero, nombre=2, equipement='pique')
        with self.soldats.bataille_complete('cascade', self.profil):
            resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil)
        self.assertEqual(resultat['affrontements'], 3)
        self.assertEqual(self.fiche(general)['progression_combat'], 1)

    def test_manoeuvre_seule_compte_et_bloc_vide_ne_compte_pas(self):
        general = self.creer(nature='stratege')
        ennemi = self.adversaire()
        unite = ennemi['chemin'] / 'avant/infanterie1'
        unite.rename(ennemi['chemin'] / 'arriere/infanterie1')
        with self.soldats.bataille_complete('sans-choc', self.profil):
            self.assertIsNone(self.choc(general, ennemi))
        self.assertEqual(self.fiche(general)['progression_combat'], 0)
        with self.soldats.bataille_complete('manoeuvre', self.profil):
            self.assertIsNone(self.choc(general, ennemi))
            armee = {g['joueur']: self.generaux.lire_blocs_general(g['chemin']) for g in (general, ennemi)}
            with patch.object(self.combats, 'combat_bloc', return_value=(1, 1)):
                self.combats.attaque_ciblee(armee, general, ennemi, 'avant', 'arriere')
        self.assertEqual(self.fiche(general)['progression_combat'], 1)

    def test_trois_tours_reserve_et_independance_jauges(self):
        general = self.creer(territoire='village', reserve=True, nature='stratege')
        self.preparer_points(general, progression_combat=1, evolution_apprise=201)
        for tour in (1, 2, 3):
            self.formation.ouvrir_tour(self.profil, tour)
            self.terminer(tour)
            fiche = self.fiche(general)
            self.assertEqual((fiche['niveau'], fiche['progression_formation']), (tour // 3, tour % 3))
            self.assertEqual(fiche['progression_combat'], 1)
        self.progression.valider_evenement(general, 'combat', 'suivant')
        self.assertEqual(self.fiche(general)['niveau'], 2)

    def test_sejour_reserve_incomplet_et_voisin_independant(self):
        general = self.creer(territoire='village', reserve=True)
        self.formation.ouvrir_tour(self.profil, 1)
        self.creer(numero=2, territoire='village', reserve=True)
        self.terminer(1)
        self.assertEqual(self.fiche(general)['progression_formation'], 1)
        self.formation.ouvrir_tour(self.profil, 2)
        ailleurs = self.config.game_path / 'village/j1/garnison/1/general1'
        general['chemin'].rename(ailleurs)
        ailleurs.rename(general['chemin'])
        self.terminer(2)
        self.assertEqual(self.fiche(general)['progression_formation'], 1)

    def test_reprise_apres_persistance_repare_fiche_sans_double_recompense(self):
        general = self.creer(nature='stratege')
        self.preparer_points(general, progression_combat=1, evolution_apprise=201)
        with patch.object(self.progression, 'publier_fiche', side_effect=OSError('interruption')):
            with self.assertRaises(OSError):
                self.progression.valider_evenement(general, 'combat', 'une-bataille')
        avant = self.fiche(general)
        importlib.reload(self.progression)
        with patch.object(self.progression, 'monter_niveau', side_effect=AssertionError('double récompense')):
            self.assertFalse(self.progression.valider_evenement(general, 'combat', 'une-bataille'))
        self.assertEqual(self.fiche(general), avant)
        texte = (general['chemin'] / 'fiche.txt').read_text()
        self.assertIn('niveau=1', texte)
        self.assertNotIn('progressions_validees', texte)

    def test_cycle_formation_avant_combat_et_republication_idempotente(self):
        general = self.creer(territoire='village', reserve=True, nature='stratege_hybride')
        self.preparer_points(general, progression_formation=2, progression_combat=1,
                            evolution_apprise=202, moral=0)
        self.formation.ouvrir_tour(self.profil, 1)
        self.formation.clore_tour(self.profil, 1)
        # Deux événements attestés au même cycle : l'ordre du pilote est fixe.
        self.formation.resoudre_tour(self.profil, 1)
        self.progression.valider_evenement(general, 'combat', 'survie:1:village')
        fiche = self.fiche(general)
        self.assertEqual((fiche['niveau'], fiche['progression_combat'], fiche['progression_formation']), (2, 0, 0))
        self.assertEqual(fiche['progressions_validees']['formation:1:j1:general1']['recompense'], 202)
        self.assertIn(fiche['progressions_validees']['combat:survie:1:village']['recompense'], (201, 1002, 105, 110))
        self.formation.resoudre_tour(self.profil, 1)
        self.progression.valider_evenement(general, 'combat', 'survie:1:village')
        self.assertEqual(self.fiche(general), fiche)

    def test_hybrides_progression_automatique_native_et_garantie_croisee(self):
        for numero, nature, garantie in ((1, 'stratege_hybride', 202), (2, 'instinctif_hybride', 201)):
            general = self.creer(numero=numero, nature=nature, place=str(numero))
            self.preparer_points(general, progression_combat=1, evolution_apprise=garantie)
            trait = self.fiche(general)['trait_inne']
            self.progression.valider_evenement(general, 'combat', 'garanti')
            self.assertIn(garantie, self.fiche(general)['evolutions_acquises'])
            for evenement in ('a', 'b'):
                self.progression.valider_evenement(general, 'combat', evenement)
            fiche = self.fiche(general)
            recompense = fiche['progressions_validees']['combat:b']['recompense']
            self.assertIn(recompense, (201, 1002, 105, 110) if numero == 1 else
                          (202, 104, 105, 106, 107, 108, 109))
            self.assertEqual((fiche['nature'], fiche['trait_inne']), (nature, trait))

    def test_home_ancien_nouvelles_unites_toutes_activites_gratuites(self):
        destinations = ('j1/reserve', 'j1/garnison/1', 'j1/hopital/1',
                        'ecole_officiers/1/j1', 'forge/1/j1')
        for numero, relatif in enumerate(destinations, 1):
            origine = self.general(numero=numero, territoire='home', nombre=1)
            unite = origine / 'avant/infanterie2'
            unite.mkdir()
            (unite / 'arc').touch()
            destination = self.config.game_path / 'village' / relatif / origine.name
            origine.rename(destination)
            self.securite.verifier_tous_les_deplacements(self.profil)
            self.assertTrue((destination / 'avant/infanterie2/arc').exists())
            identite = f'j1:general{numero}'
            self.assertEqual(self.etat.charger_positions_generaux()[identite], 'village')
            self.assertNotIn(identite, self.etat.charger_generaux_fatigues())

    def test_forge_nouveau_recette_complete_refuse_puis_publication_autorise(self):
        general = self.forge(nombre=0)
        unite = general['chemin'] / 'avant/cavalerie1'
        unite.mkdir()
        for nom in ('cheval', 'cuirasse', 'armure', 'casque', 'bouclier'):
            (unite / nom).write_text('équipement', encoding='utf-8')
        self.formation.ouvrir_tour(self.profil, 1)
        avant = {p.name: p.read_bytes() for p in unite.iterdir()}
        self.terminer(1)
        self.assertEqual({p.name: p.read_bytes() for p in unite.iterdir()}, avant)
        self.assertIn('absence de validation officielle', self.config.rapport_long_path.read_text())
        self.assertIn('unités conservées', (general['chemin'] / 'formation_resultat.txt').read_text())
        self.securite.memoriser_unites_actions(self.profil, 2)
        self.formation.ouvrir_tour(self.profil, 2)
        self.terminer(2)
        self.assertTrue((unite.parent / 'cavalerie_L1').exists())

    def test_forge_copie_uuid_et_renommage_ne_valident_pas_un_soldat(self):
        general = self.forge()
        ancienne = general['chemin'] / 'avant/cavalerie1'
        self.soldats.terminer_bataille([ancienne], 'ancienne')
        nouvelle = general['chemin'] / 'arriere/cavalerie8'
        shutil.copytree(ancienne, nouvelle)
        nouvelle.rename(nouvelle.with_name('cavalerie9'))
        nouvelle = nouvelle.with_name('cavalerie9')
        self.soldats.synchroniser(self.profil)
        self.formation.ouvrir_tour(self.profil, 1)
        avant = {p.name: p.read_bytes() for p in nouvelle.iterdir()}
        self.terminer(1)
        self.assertTrue((ancienne.parent / 'cavalerie_L1').exists())
        self.assertEqual({p.name: p.read_bytes() for p in nouvelle.iterdir()}, avant)

    def test_forge_cavalier_valide_deplace_renomme_reste_eligible(self):
        general = self.forge()
        source = general['chemin'] / 'avant/cavalerie1'
        cible = general['chemin'] / 'arriere/cavalerie9'
        source.rename(cible)
        self.formation.ouvrir_tour(self.profil, 1)
        self.terminer(1)
        self.assertTrue((cible.parent / 'cavalerie_L9').exists())

    def test_forge_sans_reference_et_nouveau_general_ne_prouvent_pas_anciennete(self):
        general = self.forge()
        reference = self.etat.charger_unites_actions(self.profil)
        reference['premiers_deploiements'] = ['j1:general1']
        self.etat.sauvegarder_unites_actions(self.profil, reference)
        self.formation.ouvrir_tour(self.profil, 1)
        self.terminer(1)
        self.assertTrue((general['chemin'] / 'avant/cavalerie1').exists())
        (self.config.game_path / '.systeme/unites_actions.json').unlink()
        self.formation.ouvrir_tour(self.profil, 2)
        self.terminer(2)
        self.assertTrue((general['chemin'] / 'avant/cavalerie1').exists())

    def test_formation_cycle_capture_publication_reprise_sans_rejeu(self):
        general = self.creer(territoire='village', reserve=True, nature='stratege')
        self.preparer_points(general, progression_formation=2, evolution_apprise=201)
        self.formation.ouvrir_tour(self.profil, 1)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        fiche = self.fiche(general)
        self.assertEqual((fiche['niveau'], fiche['progression_formation']), (1, 0))
        self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual(self.fiche(general), fiche)

    def test_combat_cycle_capture_publie_niveau_et_recu(self):
        general = self.creer(territoire='est_3', nature='stratege', nombre=20)
        self.adversaire(nombre=2)
        self.preparer_points(general, progression_combat=1, evolution_apprise=201)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        fiche = self.fiche(general)
        self.assertEqual((fiche['niveau'], fiche['progression_combat']), (1, 0))
        self.assertEqual(fiche['progressions_validees']['combat:survie:1:est_3']['recompense'], 201)
        self.assertIn('niveau=1', (general['chemin'] / 'fiche.txt').read_text())

    def test_aucune_recompense_disponible_ninvente_pas_de_gain(self):
        general = self.creer(nature='instinctif')
        acquis = [i for i, e in self.progression.evolutions_eligibles(
            self.fiche(general), apprentissage=False).items() if e['categorie'] in ('unite', 'ordre')]
        self.preparer_points(general, progression_combat=1, evolutions_acquises=acquis)
        with patch.object(self.progression.aleatoire_progression, 'randint', side_effect=AssertionError('tirage')):
            self.progression.valider_evenement(general, 'combat', 'sans-recompense')
        fiche = self.fiche(general)
        self.assertEqual((fiche['niveau'], fiche['moral'], fiche['progression_combat']), (1, 100, 0))
        self.assertIsNone(fiche['progressions_validees']['combat:sans-recompense']['recompense'])

    def test_reprise_meme_bataille_ni_point_ni_experience_soldat_en_double(self):
        general = self.creer(nature='stratege')
        ennemi = self.adversaire()
        for _ in range(2):
            with self.soldats.bataille_complete('identite-stable', self.profil):
                self.soldats.participer(general)
                self.choc(general, ennemi)
            importlib.reload(self.soldats)
            importlib.reload(self.progression)
        self.assertEqual((self.fiche(general)['progression_combat'], self.fiche(general)['niveau']), (1, 0))
        unite = self.infos(general)['unites'][0]
        self.assertEqual(self.soldats.charger()[self.soldats.marqueur(unite)]['batailles'], 1)

    def test_reprise_formation_apres_niveau_avant_cloture_du_sejour(self):
        general = self.creer(territoire='village', reserve=True, nature='stratege')
        self.preparer_points(general, progression_formation=2, evolution_apprise=201)
        self.formation.ouvrir_tour(self.profil, 1)
        self.formation.clore_tour(self.profil, 1)
        with patch.object(self.formation, 'sauvegarder', side_effect=OSError('interruption')):
            with self.assertRaises(OSError):
                self.formation.resoudre_tour(self.profil, 1)
        avant = self.fiche(general)
        self.assertEqual(avant['niveau'], 1)
        importlib.reload(self.formation)
        with patch.object(self.progression, 'monter_niveau', side_effect=AssertionError('double niveau')):
            self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual(self.fiche(general), avant)
        self.assertIn('1:j1:general1', self.formation.charger()['valides'])

    def test_general_detruit_copie_home_ne_donne_pas_de_survie(self):
        general = self.creer(nature='stratege')
        ennemi = self.adversaire()
        self.preparer_points(general, progression_combat=1)
        copie = self.racine / 'home/j1/general1'
        shutil.copytree(general['chemin'], copie)
        with self.soldats.bataille_complete('mort-avec-copie', self.profil):
            self.choc(general, ennemi, (0, 1))
            self.generaux.supprimer_general_si_vide(general)
        self.assertEqual((self.fiche(general)['progression_combat'], self.fiche(general)['niveau']), (1, 0))
        self.assertTrue(copie.exists())


if __name__ == '__main__':
    unittest.main()
