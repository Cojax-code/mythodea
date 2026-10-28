"""Contrats du raccordement non destructif des ordres V2."""
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import ordres_pipeline


class PipelineOrdresTest(unittest.TestCase):
    def test_catalogue_ids_et_jetons_uniques_y_compris_reservations(self):
        import catalogues
        ordres = catalogues.ORDRES
        jetons = [o['jeton'] for o in ordres.values()]
        noms = [o['nom'] for o in ordres.values()]
        self.assertEqual(len(jetons), len(set(jetons)))
        self.assertEqual(len(noms), len(set(noms)))
        attendus = {
            1020: ('3-5', 'charge_suicidaire', 'individuelle', False),
            1021: ('1-10', 'retrait_tactique', 'globale', True),
            1022: ('1-11', 'pour_l_honneur', 'globale', False),
            1023: ('1-12', 'ralliement', 'globale', False),
            1024: ('2-7', 'chat_man', 'duel', True),
            1025: ('1-13', 'reserve_strategique', 'globale', False),
            1026: ('2-8', 'derniere_charge', 'duel', True),
        }
        for identifiant, (jeton, nom, categorie, contre) in attendus.items():
            ordre = ordres[identifiant]
            self.assertEqual((ordre['jeton'], ordre['nom'], ordre['categorie'],
                              ordre['contre']), (jeton, nom, categorie, contre))
            self.assertFalse(ordre['disponible'])
            self.assertFalse(ordre['progression'])

    def test_formations_nactivent_pas_muraille_absente_du_catalogue(self):
        import catalogues
        # Aucun jeton officiel Muraille n'existe pour le moment.
        self.assertFalse(any(ordre['nom'] == 'muraille_humaine'
                             and ordre['disponible']
                             for ordre in catalogues.ORDRES.values()))
        self.assertTrue(catalogues.ORDRES[1015]['disponible'])
        self.assertTrue(catalogues.ORDRES[1016]['disponible'])

    def test_muraille_territoriale_exclut_qg_reserve_et_zombie(self):
        a = dict(joueur='j1', nom='general1', emplacement='1')
        b = dict(joueur='j1', nom='general2', emplacement='2')
        c = dict(joueur='j1', nom='general3', emplacement='3')
        d = dict(joueur='j1', nom='general4', emplacement='4')
        forces = {'camp': {'1': a, '2': b, '3': c, '4': d}}
        formations = {'camp': {'ordres': {'muraille_humaine', 'qg_nommade'},
                               'qg': ('j1', 'general1')}}
        with patch('generaux.general_a_des_unites', return_value=True), patch.object(
                ordres_pipeline.progression, 'general_recoit_ordre',
                side_effect=lambda g, _nom: g is not d):
            participants = ordres_pipeline.participants_muraille_territoire(
                forces, formations, 'camp', reserve_strategique=('j1', 'general2'))
        self.assertEqual(participants, (c,))
        self.assertEqual(ordres_pipeline.participants_muraille_territoire(
            forces, {}, 'camp'), ())

    def test_zombie_ordres_officiels_filtrent_meme_les_anciens_acquis(self):
        from copy import deepcopy
        import catalogues
        ids = list(catalogues.ORDRES)
        general = dict(joueur='j1', nom='general1', total_unites=2,
            caracteristiques=dict(etat_zombie=False),
            ordres=[dict(identifiant=o['jeton']) for o in catalogues.ORDRES.values()])
        avant = deepcopy(general)
        officiel = dict(nature='stratege', etat_zombie=True, evolutions_acquises=ids)
        with patch.object(ordres_pipeline.progression, 'caracteristiques_general', return_value=officiel):
            donneurs = ordres_pipeline.donneurs_officiels({'camp': {'1': general}})
        self.assertEqual([d['identifiants'] for d in donneurs], [[1012]])
        self.assertEqual(general, avant)
        officiel['evolutions_acquises'] = []
        with patch.object(ordres_pipeline.progression, 'caracteristiques_general', return_value=officiel):
            self.assertEqual(ordres_pipeline.donneurs_officiels({'camp': {'1': general}}), [])

    def setUp(self):
        self.cat = {
            1002: dict(jeton="1-2", disponible=True, categorie="globale", contre=False),
            1003: dict(jeton="2-1", disponible=False, categorie="duel", contre=False),
            1006: dict(jeton="2-3", disponible=True, categorie="duel", contre=False),
        }

    @staticmethod
    def general(jeton, specification=None):
        return {"total_unites": 2, "ordres": [
            {"identifiant": jeton, "specification": specification}]}

    def test_pas_de_fusion_entre_generaux(self):
        forces = {"camp1": {"1": self.general("1-2"), "2": self.general("2-3")},
                  "camp2": {"1": self.general("2-1"), "2": None}}
        groupes = ordres_pipeline.ordres_par_donneur(forces, catalogue=self.cat)
        self.assertEqual([(g["camp"], g["position"], g["identifiants"]) for g in groupes],
                         [("camp1", "1", [1002]), ("camp1", "2", [1006])])

    def test_ordres_inactifs_et_specifications_non_validees_ignores(self):
        self.assertEqual(ordres_pipeline.ordres_du_general(
            self.general("2-1"), catalogue=self.cat), [])
        self.assertEqual(ordres_pipeline.ordres_du_general(
            self.general("2-3", 4), catalogue=self.cat), [])
        self.assertEqual(ordres_pipeline.ordres_du_general(
            self.general("1-2"), categorie="duel", catalogue=self.cat), [])

    def test_identifiants_dedoublonnes_et_ordre_conserve(self):
        general = {"ordres": [
            {"identifiant": "2-3", "specification": None},
            {"identifiant": "1-2", "specification": None},
            {"identifiant": "2-3", "specification": None}]}
        self.assertEqual(ordres_pipeline.ordres_du_general(general, catalogue=self.cat),
                         [1006, 1002])

    def test_jetons_ambigus_refuses(self):
        cat = dict(self.cat)
        cat[2000] = dict(cat[1002])
        with self.assertRaises(ValueError):
            ordres_pipeline.index_jetons(cat)


    def test_confrontation_egalite_annule_deux_ordres_normaux(self):
        a = {"general": {"ordres": [{"identifiant": "1-2"}],
                         "caracteristiques": {"nature": "stratege", "evolutions_acquises": []}}}
        b = {"general": {"ordres": [{"identifiant": "2-3"}],
                         "caracteristiques": {"nature": "stratege", "evolutions_acquises": []}}}
        # Même catégorie nécessaire : deux ordres de catégories différentes
        # ne sont pas comparés entre eux.
        self.assertEqual(ordres_pipeline.confronter_intentions(
            a, b, "globale", 10, 10, self.cat)["camp_1"], [1002])
        duel_cat = {
            10: dict(jeton="2-1", categorie="duel", disponible=True, contre=False),
            11: dict(jeton="2-2", categorie="duel", disponible=True, contre=False),
        }
        a["general"]["ordres"] = [{"identifiant": "2-1"}]
        b["general"]["ordres"] = [{"identifiant": "2-2"}]
        self.assertEqual(ordres_pipeline.confronter_intentions(
            a, b, "duel", 10, 10, duel_cat),
            {"comparaison": 0, "camp_1": [], "camp_2": []})

    def test_contre_ordre_face_a_ordre_agissent_ensemble(self):
        cat = {
            10: dict(jeton="2-1", categorie="duel", disponible=True, contre=False),
            11: dict(jeton="2-2", categorie="duel", disponible=True, contre=True),
        }
        def donneur(jeton):
            return {"general": {
                "ordres": [{"identifiant": jeton}],
                "caracteristiques": {"nature": "instinctif", "evolutions_acquises": []}}}
        self.assertEqual(ordres_pipeline.confronter_intentions(
            donneur("2-1"), donneur("2-2"), "duel", 2, 12, cat),
            {"comparaison": -1, "camp_1": [10], "camp_2": [11]})

    def test_contre_ordre_sans_adversaire_et_rejet_entree_sans_fiche(self):
        cat = {11: dict(jeton="2-2", categorie="duel",
                        disponible=True, contre=True)}
        donneur = {"general": {
            "ordres": [{"identifiant": "2-2"}],
            "caracteristiques": {"nature": "stratege", "evolutions_acquises": []}}}
        self.assertEqual(ordres_pipeline.confronter_intentions(
            donneur, None, "duel", 9, 10, cat)["camp_1"], [11])
        with self.assertRaises(ValueError):
            ordres_pipeline.confronter_intentions(
                {"general": {"ordres": [{"identifiant": "2-2"}]}},
                None, "duel", 9, 10, cat)


    def test_donneurs_officiels_provient_du_stockage_prive(self):
        general = self.general("1-2")
        general.update({"joueur": "j1", "nom": "officier",
                        "fiche": {"nature": "instinctif"}})
        forces = {"camp1": {"1": general}}
        officiel = {"nature": "stratege", "evolutions_acquises": [],
                    "points_commandement": 12}
        with patch.object(ordres_pipeline.progression, "caracteristiques_general",
                          return_value=officiel) as lecture:
            groupes = ordres_pipeline.donneurs_officiels(
                forces, categorie="globale", catalogue=self.cat)
        self.assertEqual(len(groupes), 1)
        self.assertEqual(groupes[0]["general"]["caracteristiques"]["nature"], "stratege")
        self.assertEqual(groupes[0]["general"]["fiche"]["nature"], "instinctif")
        self.assertEqual(groupes[0]["identifiants"], [1002])
        lecture.assert_called_once_with(general)
        self.assertNotIn("caracteristiques", general)

    def test_donneur_sans_progression_officielle_est_refuse(self):
        general = self.general("1-2")
        forces = {"camp1": {"1": general}}
        with patch.object(ordres_pipeline.progression, "caracteristiques_general",
                          return_value=None):
            with self.assertRaises(ValueError):
                ordres_pipeline.donneurs_officiels(forces, catalogue=self.cat)


    def test_calcul_pc_duel_depuis_donnees_officielles(self):
        general = {"joueur": "j1", "nom": "g1", "chemin": "/factice/g1",
                   "fiche": {"points_commandement": 999}}
        prive = {"nature": "stratege", "points_commandement": 18}
        composition = {"avant": {"piquier": 2}, "arriere": {"archer": 1}}
        with patch.object(ordres_pipeline.progression, "caracteristiques_general",
                          return_value=prive), patch(
                "generaux.lire_composition_general", return_value=composition), patch.object(
                ordres_pipeline.commandement, "effectif_general",
                return_value=9) as calcul:
            self.assertEqual(ordres_pipeline.points_duel_officiels(general), 9)
        calcul.assert_called_once_with(prive, composition)

    def test_duel_avec_comparaison_reelle_et_donneurs_explicites(self):
        cat = {
            10: dict(jeton="2-1", categorie="duel", disponible=True, contre=False),
            11: dict(jeton="2-2", categorie="duel", disponible=True, contre=False),
        }
        def donneur(jeton):
            return {"general": {
                "ordres": [{"identifiant": jeton}],
                "caracteristiques": {"nature": "stratege", "evolutions_acquises": []}}}
        with patch.object(ordres_pipeline, "points_duel_officiels", side_effect=[7, 7]) as pts:
            resultat = ordres_pipeline.confronter_duel_officiel(
                {"nom": "g1"}, {"nom": "g2"},
                donneur("2-1"), donneur("2-2"), cat)
        self.assertEqual(resultat, {"comparaison": 0, "camp_1": [], "camp_2": []})
        self.assertEqual(pts.call_count, 2)

    def test_refuse_pc_prives_absents(self):
        with patch.object(ordres_pipeline.progression, "caracteristiques_general",
                          return_value=None):
            with self.assertRaises(ValueError):
                ordres_pipeline.points_duel_officiels({"chemin": "/factice"})


    def test_qg_donneur_duel_utilise_ses_pc_pas_ceux_du_combattant(self):
        cat = {
            10: dict(jeton="2-1", categorie="duel", disponible=True, contre=False),
            11: dict(jeton="2-2", categorie="duel", disponible=True, contre=False),
        }
        def donneur(nom, jeton):
            return {"general": {"nom": nom,
                "ordres": [{"identifiant": jeton}],
                "caracteristiques": {"nature": "stratege", "evolutions_acquises": []}}}
        qg = donneur("qg", "2-1")
        ennemi = donneur("ennemi", "2-2")
        combattant = {"nom": "combattant_sans_ordre"}
        def pc(general):
            return {"qg": 18, "ennemi": 12}[general["nom"]]
        with patch.object(ordres_pipeline, "points_duel_officiels", side_effect=pc) as lecture:
            resultat = ordres_pipeline.confronter_duel_officiel(
                combattant, {"nom": "combattant_ennemi"}, qg, ennemi, cat)
        self.assertEqual(resultat, {"comparaison": 1, "camp_1": [10], "camp_2": []})
        self.assertEqual([c.args[0]["nom"] for c in lecture.call_args_list],
                         ["qg", "ennemi"])


if __name__ == "__main__":
    unittest.main()
