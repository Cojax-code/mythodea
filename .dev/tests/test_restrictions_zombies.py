"""Propriété et ordres Zombies : profils privés, formations et combat ordinaire."""
import copy
import random
import unittest
from unittest.mock import patch

import test_formations_v2 as aides
import ordres_pipeline


class RestrictionsZombies(unittest.TestCase):
    setUp = aides.FormationsEnBataille.setUp
    activer = aides.FormationsEnBataille.activer
    general = aides.FormationsEnBataille.general
    creer = aides.FormationsEnBataille.creer
    infos = aides.FormationsEnBataille.infos
    modules = aides.FormationsEnBataille.modules
    speciale = aides.FormationsEnBataille.speciale
    troupe = aides.FormationsEnBataille.troupe
    ordres = aides.FormationsEnBataille.ordres
    declarer = aides.FormationsEnBataille.declarer
    qg = aides.FormationsEnBataille.qg
    bataille = aides.FormationsEnBataille.bataille
    forces = aides.FormationsEnBataille.forces
    ordre_effectif = aides.FormationsEnBataille.ordre_effectif

    def zombie(self, joueur='j1', numero=3, place='3', nombre=3):
        g = self.troupe(joueur, 'zombie', nombre, numero=numero, place=place)
        self.ordres(g, etat_zombie=True)
        return g

    def test_catalogue_tous_les_ordres_classiques_refuses_par_profil_prive(self):
        z = self.zombie()
        fiche = self.progression.caracteristiques_general(z)
        autorises = {'spora_adicte', 'propagafion'}
        for ordre in self.combats.catalogues.ORDRES.values():
            nom = ordre['nom']
            self.assertEqual(self.progression.ordre_autorise(fiche, nom), nom in autorises)
            self.assertEqual(self.progression.general_recoit_ordre(z, nom), nom in autorises)
        contexte = {ordres_pipeline.identite(z): dict(effets=set(self.combats.catalogues.ORDRES))}
        jeton = ordres_pipeline._duel.set(contexte)
        self.addCleanup(ordres_pipeline._duel.reset, jeton)
        z['caracteristiques'] = dict(etat_zombie=False)
        for identifiant in contexte[ordres_pipeline.identite(z)]['effets']:
            self.assertEqual(ordres_pipeline.effet(z, identifiant),
                             self.combats.catalogues.ORDRES[identifiant]['nom'] in autorises)

    def test_unites_zombies_interdites_audit_et_publication_sans_sanction_inventee(self):
        for numero, type_unite in enumerate(('zombie', 'Trop_gros_zombie'), 1):
            g = self.troupe('j1', type_unite, 1, numero=numero, place=str(numero))
            self.ordres(g, etat_zombie=False)
            g['caracteristiques'] = dict(etat_zombie=True)
            registre = copy.deepcopy(self.soldats.charger())
            chemin = next((g['chemin'] / 'avant').iterdir())
            with self.assertRaisesRegex(ValueError, 'réservée à un général Zombie'):
                self.securite.auditer_unites_speciales(self.profil)
            with self.assertRaisesRegex(ValueError, 'publication refusée'):
                self.soldats.synchroniser(self.profil, publication=True)
            self.assertTrue(chemin.exists())
            self.assertEqual(self.soldats.charger(), registre)
            self.ordres(g, etat_zombie=True)
            self.securite.auditer_unites_speciales(self.profil)
            self.soldats.synchroniser(self.profil, publication=True)

    def test_transfert_zombie_authentique_vers_general_ordinaire_refuse(self):
        z = self.zombie(numero=1, place='1', nombre=1)
        ordinaire = self.troupe('j1', 'piquier', 1, numero=2, place='2')
        self.ordres(ordinaire)
        ancien = self.infos(z)['unites'][0]
        identifiant = self.soldats.marqueur(ancien)
        destination = ordinaire['chemin'] / 'arriere' / ancien.name
        ancien.rename(destination)
        with self.assertRaisesRegex(ValueError, 'général Zombie'):
            self.securite.auditer_unites_speciales(self.profil)
        self.assertTrue(destination.exists())
        self.assertFalse(self.soldats.charger()[identifiant].get('detruit'))

    def test_formations_reorganisent_seulement_eligibles_sans_deplacer_zombie(self):
        a = self.troupe('j1', 'piquier', numero=1, place='1')
        d = self.troupe('j1', 'piquier', numero=4, place='4')
        self.ordres(a)
        self.ordres(d)
        z = self.zombie()
        qg = self.qg('j1', [1015, 1016])
        for ids, attendu in (([1015], ['4', '2', '3', '1']),
                             ([1016], ['1', '4', '3', '2']),
                             ([1015, 1016], ['4', '1', '3', '2'])):
            self.ordres(qg, ids)
            profils = self.progression.charger()
            profils['j1:general2']['nature'] = 'stratege'
            self.progression.sauvegarder(profils)
            with self.bataille():
                self.assertEqual(self.ordre_effectif('j1'), attendu)
                self.assertEqual(self.ordre_effectif('j1')[2], z['emplacement'])

    def test_places_vacantes_et_plusieurs_zombies_conservent_ordre_normal(self):
        z1 = self.zombie(numero=1, place='1')
        z3 = self.zombie(numero=3, place='3')
        a = self.troupe('j1', 'piquier', numero=4, place='4')
        self.ordres(a)
        formation = dict(ordres={'on_melange', 'qg_nommade'}, qg=('j1', 'general4'))
        resultat = ordres_pipeline.generaux_en_formation([z1, z3, a], formation)
        self.assertEqual([g['emplacement'] for g in resultat], ['1', '3', '4'])
        formation['qg'] = ordres_pipeline.identite(z1)
        self.assertFalse(ordres_pipeline.qg_hors_formation(z1, formation))

    def test_frontal_ignore_zombie_sans_empecher_duel_normal_des_autres(self):
        a = self.troupe('j1', 'piquier', numero=1, place='1')
        b = self.troupe('j2', 'piquier', numero=1, place='1')
        z = self.zombie(numero=2, place='2')
        ennemi = self.troupe('j2', 'archer', 10, numero=2, place='2')
        for g in (a, b, ennemi):
            self.ordres(g)
        self.ordres(z, [1002], texte='1-2', etat_zombie=True)
        z['ordres'] = self.generaux.lire_ordres_general(z['chemin'])
        self.assertFalse(self.generaux.general_possede_ordre(z, '1-2'))
        with self.bataille() as contexte, \
                patch.object(self.combats, 'combat_entre_generaux', return_value={}) as combattre, \
                patch.object(self.combats.rapports, 'ecrire_ligne_affrontement_territoire'):
            resultats = self.combats.resoudre_attaque_frontale(
                self.config.game_path / 'est_3', 'OFF/OFF', contexte['configuration'])
        self.assertEqual([p for p, _ in resultats], ['1'])
        combattre.assert_called_once()
        # Ignorer le frontal n'est ni une protection ni une disparition du combat.
        resultat = self.combats.combat_entre_generaux(z, ennemi)
        self.assertEqual(resultat['initial_1'], 3)
        self.assertEqual(resultat['final_1'], 0)

    def test_muraille_preparee_ignore_zombie_mais_garde_avants_eligibles(self):
        z = self.zombie(numero=1, place='1')
        a = self.troupe('j1', 'piquier', 5, numero=2, place='2')
        b = self.troupe('j2', 'cavalier', 2)
        self.ordres(a)
        self.ordres(b)
        resultat = self.combats.prochain_avant_muraille([z, a], b, aleatoire=random.Random(0))
        self.assertEqual(resultat['choisi'], ('j1', 'general2'))
        self.assertEqual([p['origine'] for p in resultat['previsions']], [('j1', 'general2')])
        self.assertEqual(self.infos(z)['nombre'], 3)

    def test_choca_fuite_et_gros_poisson_ignores_meme_sous_qg_ordinaire(self):
        z = self.zombie(numero=1, place='1')
        b = self.troupe('j2', 'piquier')
        self.ordres(b)
        qg = self.qg('j1', [1011, 1017], nature='instinctif')
        (qg['chemin'] / 'ordre.txt').write_text('2-5\n2-6-1-2', encoding='utf-8')
        with self.bataille(), ordres_pipeline.retraites_apres_choc(lambda g: self.fail('Zombie en fuite')):
            with ordres_pipeline.duel(z, b):
                self.assertFalse(ordres_pipeline.effet(z, 1017))
                self.assertFalse(ordres_pipeline.effet(z, 1011))
                self.assertEqual(ordres_pipeline.fuir_apres_choc((z, b)), [])


if __name__ == '__main__':
    unittest.main()
