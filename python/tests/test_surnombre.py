"""Ordres individuels, retraites et cascades avec le moteur réel en isolation."""
import contextlib
import io
import unittest
from unittest.mock import call, patch

import test_vagues


class Surnombre(unittest.TestCase):
    def setUp(self):
        # Même plateau temporaire et mêmes propriétaires Unix simulés que les vagues.
        test_vagues.VaguesEst.setUp(self)
        self.contextes.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.plateau.reparer_structure(self.profil)
        self.survie.preparer_zones_bot(self.profil)
        self.contextes.enter_context(patch.object(
            self.securite, "joueur_proprietaire_chemin",
            lambda chemin: next((j for j in self.profil["joueurs"] if j in chemin.parts), None)))

    def general(self, joueur="j1", numero=1, territoire="est_3", place="1",
                nombre=20, equipement="arc", ordre=None, reserve=False):
        if territoire == "home":
            parent = self.racine / "home" / joueur
        elif territoire == "repli":
            parent = self.config.repli_path / joueur
        elif joueur == "bot":
            self.survie.preparer_zones_bot(self.profil)
            parent = self.survie.destination_ennemi(
                self.config.game_path / territoire, f"general{numero}", self.profil).parent
        else:
            zones = self.generaux.zones_generaux_territoire(
                self.config.game_path / territoire, joueur, self.profil)
            parent = next(z["chemin"] for z in zones
                          if ("emplacement" not in z if reserve else z.get("emplacement") == place))
        parent.mkdir(parents=True, exist_ok=True)
        chemin = parent / f"general{numero}"
        self.generaux.creer_general(chemin, chemin.name)
        if ordre is not None:
            (chemin / "ordre_surnombre.txt").write_text(f"{ordre}\n", encoding="utf-8")
        prefixe = "cavalerie" if equipement == "cheval" else "infanterie"
        for index in range(nombre):
            unite = chemin / "avant" / f"{prefixe}{index + 1}"
            unite.mkdir()
            (unite / equipement).touch()
        if joueur == "bot":
            with (chemin / "fiche.txt").open("a", encoding="utf-8") as fichier:
                fichier.write(f"\nfaction=est\nvague=1\nnom_affichage=general1_{numero}\n")
            self.survie.enregistrer_arrivee_ennemi(self.config.game_path / territoire, chemin, self.profil)
        self.generaux.donner_permissions_general(chemin, "root" if joueur == "bot" else joueur)
        positions = self.etat.charger_positions_generaux()
        positions[f"{joueur}:{chemin.name}"] = territoire
        self.etat.sauvegarder_positions_generaux(positions)
        self.etat.sauvegarder_compteur_general(joueur, max(numero, self.etat.lire_compteur_general(joueur)))
        return chemin

    def colonne(self, nombre=10, territoire="est_3", unites=2, numeros=None):
        return [self.general("bot", numero, territoire, nombre=unites, equipement="pique")
                for numero in (numeros if numeros is not None else range(1, nombre + 1))]

    def cascade(self, territoire="est_3", mode="OFF/OFF"):
        return self.survie.resoudre_cascade(self.config.game_path / territoire, self.profil, mode)

    def scan(self):
        self.generaux.scanner_ordres_surnombre(self.profil)

    def test_scan_cree_defauts_droits_et_preserve_ordre_classique(self):
        exterieur = self.general()
        village = self.general("j2", territoire="village")
        self.colonne(1)
        self.scan()
        for chemin, attendu, uid in ((exterieur, "1\n", 1001), (village, "2\n", 1002)):
            fichier = chemin / "ordre_surnombre.txt"
            self.assertEqual(fichier.read_text(encoding="utf-8"), attendu)
            self.assertEqual((chemin / "ordre.txt").read_text(encoding="utf-8"), "1-2\n")
            self.assertIn(call(fichier, uid, uid), self.chown.call_args_list)
            self.assertIn(call(fichier, 0o600), self.chmod.call_args_list)
        self.assertFalse(list((self.config.game_path / "est_3/bot").rglob("ordre_surnombre.txt")))

    def test_scan_home_repli_reserve_et_garnison(self):
        chemins = [self.general(numero=1, territoire="home"),
                   self.general(numero=2, territoire="repli"),
                   self.general(numero=3, territoire="village", reserve=True),
                   self.general(numero=4, territoire="village")]
        self.scan()
        self.assertEqual([(p / "ordre_surnombre.txt").read_text().strip() for p in chemins],
                         ["1", "1", "2", "2"])

    def test_audit_declenche_creation_et_recreation_au_lieu_actuel(self):
        chemin = self.general(territoire="est_1")
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual((chemin / "ordre_surnombre.txt").read_text().strip(), "1")
        destination = self.config.game_path / "village/j1/garnison/1/general1"
        chemin.rename(destination)
        (destination / "ordre_surnombre.txt").unlink()
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual((destination / "ordre_surnombre.txt").read_text().strip(), "2")

    def test_choix_suit_general_et_scan_ne_le_remplace_pas(self):
        chemin = self.general(territoire="village", ordre=2)
        destination = self.config.game_path / "est_1/j1/1/general1"
        chemin.rename(destination)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.scan()
        self.assertEqual((destination / "ordre_surnombre.txt").read_text().strip(), "2")
        (destination / "ordre_surnombre.txt").unlink()
        self.scan()
        self.assertEqual((destination / "ordre_surnombre.txt").read_text().strip(), "1")

    def test_classique_sans_nouveau_fichier(self):
        chemin = self.general()
        classique = self.config.configuration_mode("classique")
        self.generaux.scanner_ordres_surnombre(classique)
        self.generaux.assurer_ordre_surnombre(chemin, "j1", "est_3", classique)
        self.assertFalse((chemin / "ordre_surnombre.txt").exists())

    def test_routes_est_et_village_sans_route_automatique(self):
        for origine, destination in (("est_3", "est_2"), ("est_2", "est_1"),
                                     ("est_1", "village"), ("village", None)):
            self.assertEqual(self.mouvements.destination_retraite_surnombre(origine, self.profil), destination)

    def test_route_ambigue_refusee_sans_inventer_un_departage(self):
        self.profil["carte_territoires"] = {
            "village": ["est_1", "est_2"], "est_1": ["village", "est_3"],
            "est_2": ["village", "est_3"], "est_3": ["est_1", "est_2"]}
        with self.assertRaisesRegex(ValueError, "départage"):
            self.mouvements.destination_retraite_surnombre("est_3", self.profil)

    def test_ordre_ne_coupe_pas_initial_et_non_consulte_sans_renforts(self):
        joueur = self.general(ordre=1)
        self.colonne(4)
        resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 1)
        self.assertEqual(resultat["retraites"], [])
        self.assertEqual(resultat["controle"], "allies")
        self.assertTrue(joueur.exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(joueur), 16)

    def test_trois_affrontements_pertes_conservees_et_ordre_arrivee(self):
        joueur = self.general(ordre=2)
        ennemis = self.colonne(numeros=range(10, 0, -1))
        fiches = {p.name: self.generaux.lire_fiche_general(p) for p in ennemis}
        effectifs_depart = []
        compositions = []
        resoudre = self.combats.resoudre_combat_range
        def observer(*args):
            effectifs_depart.append(self.generaux.total_general_depuis_chemin(joueur))
            forces = self.generaux.lire_forces_territoire(args[0], self.profil)
            actifs = self.generaux.generaux_actifs_joueur(forces, "bot")
            compositions.append([g["nom"] for g in actifs])
            for general in actifs:
                self.assertEqual(general["fiche"], fiches[general["nom"]])
            return resoudre(*args)
        with patch.object(self.combats, "resoudre_combat_range", side_effect=observer):
            resultat = self.cascade()
        self.assertEqual(resultat, {"affrontements": 3, "retraites": [], "controle": "allies"})
        self.assertEqual(effectifs_depart, [20, 16, 12])
        self.assertEqual(compositions, [["general10", "general9", "general8", "general7"],
                                       ["general6", "general5", "general4", "general3"],
                                       ["general2", "general1"]])
        self.assertEqual(self.generaux.total_general_depuis_chemin(joueur), 10)
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "est_3"})
        rapport = (self.config.rapports_territoires_dir / "est_3.txt").read_text(encoding="utf-8")
        self.assertIn("AFFRONTEMENT SURVIE 3", rapport)
        self.assertIn("general1_10", rapport)

    def test_village_interdit_retraite_meme_ordre_un(self):
        joueur = self.general(territoire="village", ordre=1)
        self.colonne(6, "village")
        resultat = self.cascade("village")
        self.assertEqual(resultat["affrontements"], 2)
        self.assertEqual(resultat["retraites"], [])
        self.assertEqual(resultat["controle"], "allies")
        self.assertTrue(joueur.exists())
        self.assertEqual((joueur / "ordre_surnombre.txt").read_text().strip(), "1")

    def test_fin_cascade_allie_detruit_renforts_intacts(self):
        joueur = self.general(nombre=1, ordre=2)
        self.colonne(10, unites=20)
        resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 1)
        self.assertEqual(resultat["controle"], "bot")
        self.assertFalse(joueur.exists())
        self.assertEqual(len(self.generaux.lire_renforts_bot(self.config.game_path / "est_3")), 6)

    def test_fin_cascade_allie_detruit_pendant_deuxieme_affrontement(self):
        joueur = self.general(nombre=5, ordre=2)
        self.colonne(10)
        resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 2)
        self.assertFalse(joueur.exists())
        self.assertEqual(resultat["controle"], "bot")

    def test_pas_de_renforts_promus_pas_de_relance_apres_limite(self):
        self.general(ordre=2)
        self.colonne(5)
        with patch.object(self.combats, "resoudre_affrontement_actif") as affrontement:
            resultat = self.cascade()
        self.assertEqual(affrontement.call_count, 1)
        self.assertEqual(resultat["controle"], "conteste")

    def test_reserve_alliee_exclue_de_la_cascade(self):
        reserve = self.general(territoire="village", reserve=True, ordre=2)
        self.colonne(6, "village")
        resultat = self.cascade("village")
        self.assertEqual(resultat["affrontements"], 0)
        self.assertEqual(self.generaux.total_general_depuis_chemin(reserve), 20)

    def test_cascade_off_def_reutilise_meme_moteur(self):
        self.general(ordre=2)
        self.colonne(5)
        resultat = self.cascade(mode="OFF/DEF")
        self.assertEqual(resultat["affrontements"], 2)
        self.assertEqual(resultat["controle"], "allies")

    def test_retraites_trois_territoires_avec_choix_et_pertes_conserves(self):
        for origine, arrivee in (("est_3", "est_2"), ("est_2", "est_1"), ("est_1", "village")):
            with self.subTest(origine=origine):
                # Des identités différentes isolent les scénarios sur le même plateau.
                numero = {"est_3": 1, "est_2": 2, "est_1": 3}[origine]
                joueur = self.general(numero=numero, territoire=origine, place="3", ordre=1)
                self.colonne(5, origine, numeros=range(numero * 10, numero * 10 + 5))
                resultat = self.cascade(origine)
                self.assertEqual(resultat["affrontements"], 1)
                self.assertEqual(len(resultat["retraites"]), 1)
                position, chemin = self.generaux.trouver_position_general("j1", f"general{numero}", self.profil)
                self.assertEqual(position, arrivee)
                # Sans préférence, la nouvelle règle cherche la première place libre.
                self.assertEqual(chemin.parent.name, "1")
                self.assertEqual((chemin / "ordre_surnombre.txt").read_text().strip(), "1")
                self.assertEqual(self.generaux.total_general_depuis_chemin(chemin), 16)
                self.assertFalse(joueur.exists())
                # Mettre le survivant hors des futurs scénarios pour éviter une collision voulue ailleurs.
                repli = self.config.repli_path / "j1" / chemin.name
                chemin.rename(repli)
                positions = self.etat.charger_positions_generaux()
                positions[f"j1:{chemin.name}"] = "repli"
                self.etat.sauvegarder_positions_generaux(positions)

    def test_un_allie_fuit_autre_continue_decisions_individuelles(self):
        j1 = self.general(ordre=1)
        j2 = self.general("j2", place="2", ordre=2)
        self.colonne()
        resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 3)
        self.assertEqual([r["joueur"] for r in resultat["retraites"]], ["j1"])
        self.assertFalse(j1.exists())
        destination = self.config.game_path / "est_2/j1/1/general1"
        self.assertEqual(self.generaux.total_general_depuis_chemin(destination), 17)
        self.assertEqual(self.generaux.total_general_depuis_chemin(j2), 13)
        self.assertEqual(self.etat.charger_positions_generaux(),
                         {"j1:general1": "est_2", "j2:general1": "est_3"})
        journal = self.config.rapport_long_path.read_text(encoding="utf-8")
        suite = journal.split("=== AFFRONTEMENT SURVIE 2")[1]
        self.assertNotIn("Engagement : j1", suite)

    def test_tous_allies_fuient_colonne_remontee_reste(self):
        self.general(ordre=1)
        self.general(numero=2, place="2", ordre=1)
        self.colonne()
        resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 1)
        self.assertEqual(len(resultat["retraites"]), 2)
        self.assertEqual(resultat["controle"], "bot")
        ennemis = self.survie.inventorier_ennemis(self.config.game_path / "est_3", self.profil)
        self.assertEqual([g["nom"] for g in ennemis], [f"general{i}" for i in range(5, 11)])
        self.assertEqual([g["emplacement"] for g in ennemis], ["1", "2", "3", "4", None, None])

    def test_ordre_reconsulte_avant_chaque_nouvel_affrontement(self):
        joueur = self.general(ordre=2)
        self.colonne()
        resoudre = self.combats.resoudre_combat_range
        compteur = 0
        def modifier_apres_deuxieme(*args):
            nonlocal compteur
            promus = resoudre(*args)
            compteur += 1
            if compteur == 2:
                (joueur / "ordre_surnombre.txt").write_text("1\n", encoding="utf-8")
            return promus
        with patch.object(self.combats, "resoudre_combat_range", side_effect=modifier_apres_deuxieme):
            resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 2)
        self.assertEqual(len(resultat["retraites"]), 1)
        self.assertEqual(self.generaux.total_general_depuis_chemin(resultat["retraites"][0]["chemin"]), 12)

    def test_ordre_supprime_entre_affrontements_recree_au_lieu_actuel(self):
        joueur = self.general(ordre=2)
        self.colonne(5)
        resoudre = self.combats.resoudre_combat_range
        def supprimer_apres_initial(*args):
            resultat = resoudre(*args)
            (joueur / "ordre_surnombre.txt").unlink()
            return resultat
        with patch.object(self.combats, "resoudre_combat_range", side_effect=supprimer_apres_initial):
            resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 1)
        chemin = resultat["retraites"][0]["chemin"]
        self.assertEqual((chemin / "ordre_surnombre.txt").read_text().strip(), "1")

    def test_ordre_invalide_defaut_signale_sans_reecriture(self):
        joueur = self.general(ordre=2)
        for texte in ("", "3", "01", "1\n2"):
            (joueur / "ordre_surnombre.txt").write_text(texte, encoding="utf-8")
            general = {"chemin": joueur, "joueur": "j1"}
            self.assertEqual(self.generaux.lire_ordre_surnombre(general, "est_3", self.profil), 1)
            self.assertEqual(self.generaux.lire_ordre_surnombre(general, "village", self.profil), 2)
            self.assertEqual((joueur / "ordre_surnombre.txt").read_text(encoding="utf-8"), texte)
        self.assertIn("Ordre de surnombre invalide", self.config.rapport_long_path.read_text(encoding="utf-8"))

    def test_arrivee_occupee_reorganise_sans_repli_ni_pertes(self):
        self.general(ordre=1)
        occupant = self.general("j2", territoire="est_2", ordre=2)
        self.colonne(5)
        resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 1)
        self.assertTrue(occupant.exists())
        for joueur, effectif in (("j1", 16), ("j2", 20)):
            place = "2" if joueur == "j1" else "1"
            chemin = self.config.game_path / "est_2" / joueur / place / "general1"
            self.assertEqual(self.generaux.total_general_depuis_chemin(chemin), effectif)
            self.assertEqual(self.etat.charger_positions_generaux()[f"{joueur}:general1"], "est_2")
        self.assertEqual(resultat["retraites"][0]["chemin"], self.config.game_path / "est_2/j1/2/general1")
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})

    def preference(self, chemin, valeur):
        with (chemin / "fiche.txt").open("a", encoding="utf-8") as fichier:
            fichier.write(f"\nposition_surnombre={valeur}\n")

    def reculer(self, chemins, origine="est_3"):
        forces = self.generaux.lire_forces_territoire(self.config.game_path / origine, self.profil)
        arrivants = [g for g in self.generaux.generaux_actifs_joueur(forces, "allies")
                     if g["chemin"] in chemins]
        return self.mouvements.retraites_surnombre(
            list(reversed(arrivants)), self.config.game_path / origine, self.profil)

    def test_preferences_prioritaires_puis_origines_numeriques(self):
        sans1 = self.general(place="1")
        avec4 = self.general("j2", place="4")
        sans3 = self.general(numero=2, place="3")
        self.preference(avec4, 1)
        resultat = self.reculer([sans1, avec4, sans3])
        self.assertEqual([(g["joueur"], g["nom"], p.parent.name) for g, p in resultat],
                         [("j2", "general1", "1"), ("j1", "general1", "2"), ("j1", "general2", "3")])

    def test_cascade_place_les_fuyards_ensemble_selon_preferences(self):
        sans = self.general(ordre=1)
        prioritaire = self.general("j2", place="2", ordre=1)
        self.preference(prioritaire, 1)
        self.colonne(5)
        resultat = self.cascade()
        self.assertEqual(resultat["affrontements"], 1)
        self.assertEqual([(r["joueur"], r["chemin"].parent.name) for r in resultat["retraites"]],
                         [("j2", "1"), ("j1", "2")])
        self.assertFalse(sans.exists())
        self.assertFalse(prioritaire.exists())

    def test_preferences_croissantes_et_chevauchement_vers_haut(self):
        premier = self.general(place="4")
        second = self.general("j2", place="1")
        self.preference(premier, 5)
        self.preference(second, 6)
        self.general(numero=2, territoire="est_2", place="5")
        resultat = self.reculer([premier, second])
        self.assertEqual([p.parent.name for _, p in resultat], ["6", "7"])
        self.assertTrue(all(p.parent.parent.name == "renforts" for _, p in resultat))

    def test_debordement_village_renforts_distincts_reserve_fatigue_et_fichiers(self):
        arrivant = self.general(territoire="est_1", ordre=1)
        for numero in range(1, 5):
            self.general("j2", numero=numero, territoire="village", place=str(numero))
        reserve = self.general(numero=2, territoire="village", reserve=True)
        self.etat.sauvegarder_generaux_fatigues({"j1:general1"})
        fichiers = {p.name: p.read_bytes() for p in arrivant.iterdir() if p.is_file()}
        resultat = self.reculer([arrivant], "est_1")
        destination = self.config.game_path / "village/j1/renforts/5/general1"
        self.assertEqual(resultat[0][1], destination)
        self.assertTrue(reserve.exists())
        self.assertEqual(self.etat.charger_positions_generaux()["j1:general1"], "village")
        self.assertEqual(self.etat.charger_generaux_fatigues(), {"j1:general1"})
        self.assertEqual(self.generaux.total_general_depuis_chemin(destination), 20)
        self.assertEqual({p.name: p.read_bytes() for p in destination.iterdir() if p.is_file()}, fichiers)
        forces = self.generaux.lire_forces_territoire(self.config.game_path / "village", self.profil)
        self.assertEqual(len(self.generaux.generaux_actifs_joueur(forces, "allies")), 4)

    def test_preference_20_acceptee_et_scan_renforts_hors_village(self):
        arrivant = self.general()
        self.preference(arrivant, 20)
        destination = self.reculer([arrivant])[0][1]
        self.scan()
        self.assertEqual(destination.parent.name, "20")
        self.assertEqual((destination / "ordre_surnombre.txt").read_text().strip(), "1")

    def test_preferences_invalides_sans_preference_avertissement_fiche_intacte(self):
        for numero, valeur in enumerate(("", "0", "21", "abc", "-1", "1.5"), 1):
            with self.subTest(valeur=valeur):
                arrivant = self.general(numero=numero, place="3")
                self.preference(arrivant, valeur)
                fiche = (arrivant / "fiche.txt").read_bytes()
                destination = self.reculer([arrivant])[0][1]
                self.assertEqual(destination.parent.name, str(numero))
                self.assertEqual((destination / "fiche.txt").read_bytes(), fiche)
                self.assertEqual(self.etat.charger_positions_generaux()[f"j1:general{numero}"], "est_2")
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})
        journal = self.config.rapport_long_path.read_text(encoding="utf-8")
        self.assertEqual(journal.count("position_surnombre invalide"), 6)

    def test_preferences_egales_departage_origines_independant_des_joueurs(self):
        for numero, joueurs in enumerate((("j2", "j1"), ("j1", "j2")), 1):
            with self.subTest(joueurs=joueurs):
                premier = self.general(joueurs[0], numero=numero, place="1")
                second = self.general(joueurs[1], numero=numero, place="3")
                self.preference(premier, 5)
                self.preference(second, 5)
                resultat = self.reculer([second, premier])
                self.assertEqual([(g["joueur"], p.parent.name) for g, p in resultat],
                                 [(joueurs[0], str(3 + 2 * numero)),
                                  (joueurs[1], str(4 + 2 * numero))])

    def test_sans_place_reste_mais_les_autres_partent(self):
        bloque = self.general(place="1")
        libre = self.general("j2", place="3")
        self.preference(bloque, 20)
        occupant = self.general(numero=2, territoire="est_2", place="20")
        fiche = (bloque / "fiche.txt").read_bytes()
        resultat = self.reculer([bloque, libre])
        self.assertEqual([(g["joueur"], p.parent.name) for g, p in resultat], [("j2", "1")])
        self.assertTrue(bloque.exists())
        self.assertTrue(occupant.exists())
        self.assertEqual((bloque / "fiche.txt").read_bytes(), fiche)
        self.assertEqual(self.generaux.total_general_depuis_chemin(bloque), 20)
        self.assertEqual(self.etat.charger_positions_generaux(),
                         {"j1:general1": "est_3", "j2:general1": "est_2", "j1:general2": "est_2"})
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})
        self.assertIn("aucune place libre entre 20 et 20", self.config.rapport_long_path.read_text(encoding="utf-8"))

    def test_file_pleine_sans_preference_reste_sans_repli(self):
        arrivant = self.general()
        for numero in range(1, 21):
            self.general("j2", numero=numero, territoire="est_2", place=str(numero))
        positions = self.etat.charger_positions_generaux()
        self.assertEqual(self.reculer([arrivant]), [])
        self.assertTrue(arrivant.exists())
        self.assertEqual(self.etat.charger_positions_generaux(), positions)
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})

    def test_preference_non_consultee_sans_retraite(self):
        general = self.general(ordre=2)
        self.preference(general, "invalide")
        self.colonne(5)
        self.assertEqual(self.cascade()["affrontements"], 2)


if __name__ == "__main__":
    unittest.main()
