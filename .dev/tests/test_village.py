"""Village Survie : vrais dossiers temporaires, propriétaires Unix simulés."""
import contextlib
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch


class Village(unittest.TestCase):
    def setUp(self):
        self.contextes = contextlib.ExitStack()
        self.addCleanup(self.contextes.close)
        self.racine = Path(self.contextes.enter_context(tempfile.TemporaryDirectory()))
        self.contextes.enter_context(patch.object(sys, "path", [
            str(Path(__file__).resolve().parents[2] / 'python'), *sys.path,
        ]))
        self.contextes.enter_context(patch.dict(sys.modules))
        noms = ("config", "etat", "rapports", "generaux", "mouvements",
                "securite", "combats", "plateau")
        for nom in noms:
            sys.modules.pop(nom, None)
        self.uids = {"j1": 1001, "j2": 1002}
        sys.modules["pwd"] = SimpleNamespace(
            getpwnam=lambda joueur: SimpleNamespace(pw_uid=self.uids[joueur]))
        sys.modules["grp"] = SimpleNamespace(
            getgrnam=lambda joueur: SimpleNamespace(gr_gid=self.uids[joueur]))
        for nom in noms:
            setattr(self, nom, importlib.import_module(nom))
        self.config.game_path = self.racine / "game"
        for nom, relatif in {
            "positions_generaux_path": ".systeme/positions_generaux.txt",
            "fatigue_generaux_path": ".systeme/fatigue_generaux.txt",
            "controle_territoires_path": ".systeme/controle_territoires.txt",
            "repli_path": "repli",
            "rapport_long_path": "rapport/rapport_long.txt",
        }.items():
            setattr(self.config, nom, self.config.game_path / relatif)
        (self.config.game_path / ".systeme").mkdir(parents=True)
        for joueur in self.config.joueurs:
            (self.racine / "home" / joueur).mkdir(parents=True)
        self.contextes.enter_context(patch.object(
            self.generaux, "Path", lambda chemin: self.racine / chemin.lstrip("/")))
        self.chown = self.contextes.enter_context(patch.object(self.plateau.os, "chown", create=True))
        self.chmod = self.contextes.enter_context(patch.object(self.plateau.os, "chmod"))
        # L'appartenance initiale est enregistrée par général, indépendamment
        # de sa zone actuelle, pour tester aussi un placement chez l'autre joueur.
        self.proprietaires = {}
        self.contextes.enter_context(patch.object(
            self.securite, "joueur_proprietaire_chemin",
            lambda chemin: self.proprietaires.get(chemin, next(
                (j for j in self.config.joueurs if j in chemin.parts), None))))
        self.profil = self.config.configuration_mode("survie")
        self.plateau.reparer_structure(self.profil)

    def chemin(self, joueur="j1", nom="general1", territoire="village", place="1", reserve=False):
        if territoire == "home":
            return self.racine / "home" / joueur / nom
        if territoire == "repli":
            return self.config.repli_path / joueur / nom
        zone = self.config.game_path / territoire / joueur
        if not reserve and int(place) >= 5:
            zone = zone / "renforts"
        elif territoire == "village":
            zone = zone / ("reserve" if reserve else "garnison")
        if not reserve:
            zone = zone / place
        return zone / nom

    def general(self, joueur="j1", nom="general1", territoire="village", place="1", reserve=False):
        chemin = self.chemin(joueur, nom, territoire, place, reserve)
        self.generaux.creer_general(chemin, nom)
        unite = chemin / "avant" / "infanterie1"
        unite.mkdir()
        (unite / "arc").touch()
        self.proprietaires[chemin] = joueur
        numero = self.generaux.numero_general_depuis_nom(nom)
        self.etat.sauvegarder_compteur_general(
            joueur, max(numero, self.etat.lire_compteur_general(joueur)))
        positions = self.etat.charger_positions_generaux()
        positions[f"{joueur}:{nom}"] = territoire
        self.etat.sauvegarder_positions_generaux(positions)
        return chemin

    def audit(self):
        self.securite.verifier_tous_les_deplacements(self.profil)

    def test_structure_village_et_droits_separes_sans_generation(self):
        for joueur, uid in self.uids.items():
            base = self.config.game_path / "village" / joueur
            for relatif in (".", "garnison", "reserve", "garnison/1", "garnison/2", "garnison/3", "garnison/4"):
                chemin = base / relatif
                self.assertTrue(chemin.is_dir())
                self.assertIn(call(chemin, uid, uid), self.chown.call_args_list)
                self.assertIn(call(chemin, 0o700), self.chmod.call_args_list)
            self.assertFalse((base / "1").exists())
            self.assertTrue((self.config.repli_path / joueur).is_dir())
            for territoire in ("est_1", "est_2", "est_3"):
                self.assertTrue((self.config.game_path / territoire / joueur / "1").is_dir())
        self.assertEqual(list(self.racine.rglob("general*")), [])
        self.assertEqual(list(self.racine.rglob("compteur*")), [])
        self.assertEqual(self.config.bases_joueurs, {"j1": "base1", "j2": "base2"})

    def test_renforts_5_a_20_prives_decouverts_et_exclus_du_combat(self):
        for territoire in ("est_1", "est_2", "est_3"):
            for joueur, uid in self.uids.items():
                for place in range(5, 21):
                    dossier = self.chemin(joueur, territoire=territoire, place=str(place)).parent
                    self.assertTrue(dossier.is_dir())
                    self.assertIn(call(dossier, uid, uid), self.chown.call_args_list)
                    self.assertIn(call(dossier, 0o700), self.chmod.call_args_list)
        for joueur in self.uids:
            self.assertFalse((self.config.game_path / 'village' / joueur / 'renforts').exists())
        renfort = self.general(territoire="est_1", place="20")
        reserve = self.general("j2", reserve=True)
        self.audit()
        self.assertEqual(self.generaux.trouver_position_general("j1", "general1", self.profil),
                         ("est_1", renfort))
        self.assertEqual((renfort / "ordre_surnombre.txt").read_text().strip(), "1")
        forces = self.generaux.lire_forces_territoire(self.config.game_path / "est_1", self.profil)
        self.assertEqual(self.generaux.controle_forces(forces), "neutre")
        self.assertTrue(reserve.exists())

    def test_identite_et_duplication_controlees_dans_renforts(self):
        renfort = self.general(territoire="est_2", place="5")
        actif = self.general(territoire="est_2")
        faux = self.chemin(nom="general2", territoire="est_2", place="20")
        self.generaux.creer_general(faux, faux.name)
        self.audit()
        self.assertFalse(renfort.exists())
        self.assertFalse(actif.exists())
        self.assertFalse(faux.exists())
        self.assertTrue(self.chemin(territoire="repli").exists())

    def test_reparation_repetee_preserve_generaux_reserve_et_garnison(self):
        reserve = self.general(reserve=True)
        garnison = self.general("j2", place="2")
        positions = self.etat.charger_positions_generaux()
        self.plateau.reparer_structure(self.profil)
        for general in (reserve, garnison):
            self.assertTrue((general / "avant/infanterie1/arc").is_file())
        self.assertEqual(self.etat.charger_positions_generaux(), positions)

    def test_reserve_vers_garnison_puis_mouvement_normal(self):
        reserve = self.general(reserve=True)
        garnison = self.chemin()
        reserve.rename(garnison)
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "village"})
        self.assertEqual(self.etat.charger_generaux_fatigues(), set())
        destination = self.chemin(territoire="est_1")
        garnison.rename(destination)
        self.audit()
        self.assertTrue(destination.is_dir())
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "est_1"})
        self.assertEqual(self.etat.charger_generaux_fatigues(), set())

    def test_garnison_vers_reserve_puis_mouvement_normal(self):
        general = self.general()
        reserve = self.chemin(reserve=True)
        general.rename(reserve)
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "village"})
        self.assertEqual(self.etat.charger_generaux_fatigues(), set())
        reserve.rename(general)
        destination = self.chemin(territoire="est_1")
        general.rename(destination)
        self.audit()
        self.assertTrue(destination.is_dir())
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "est_1"})

    def test_reorganisation_et_sortie_avant_un_seul_audit(self):
        general = self.general("j2", reserve=True)
        garnison = self.chemin("j2", place="2")
        general.rename(garnison)
        destination = self.chemin("j2", territoire="est_1", place="2")
        garnison.rename(destination)
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux(), {"j2:general1": "est_1"})
        self.assertTrue((destination / "avant/infanterie1/arc").exists())
        self.assertEqual(self.etat.charger_generaux_fatigues(), set())

    def test_collision_alliee_village_et_exterieur_envoie_les_deux_au_repli(self):
        for numero, territoire in enumerate(("village", "est_1"), 1):
            nom = f"general{numero}"
            with self.subTest(territoire=territoire):
                chemins = [self.general(j, nom, territoire) for j in ("j1", "j2")]
                self.audit()
                for joueur, ancien in zip(("j1", "j2"), chemins):
                    repli = self.chemin(joueur, nom, "repli")
                    self.assertFalse(ancien.exists())
                    self.assertTrue((repli / "avant/infanterie1/arc").is_file())
                    self.assertEqual(self.etat.charger_positions_generaux()[f"{joueur}:{nom}"], "repli")
                    self.assertIn(call(repli, self.uids[joueur], self.uids[joueur]), self.chown.call_args_list)

    def test_positions_alliees_differentes_valides(self):
        for numero, territoire in enumerate(("village", "est_2"), 1):
            for joueur, place in (("j1", "1"), ("j2", "2")):
                self.general(joueur, f"general{numero}", territoire, place)
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux(), {
            "j1:general1": "village", "j2:general1": "village",
            "j1:general2": "est_2", "j2:general2": "est_2",
        })

    def test_reserves_hors_collision_et_hors_forces_engagees(self):
        for joueur in ("j1", "j2"):
            self.general(joueur, reserve=True)
            self.general(joueur, "general2", reserve=True)
        garnison = self.general("j1", "general3")
        self.audit()
        positions = self.etat.charger_positions_generaux()
        self.assertEqual(len(positions), 5)
        self.assertEqual(set(positions.values()), {"village"})
        forces = self.generaux.lire_generaux_territoire(self.config.game_path / "village", self.profil)
        self.assertEqual(forces["j1"]["1"]["chemin"], garnison)
        self.assertTrue(all(g is None for g in forces["j2"].values()))
        for joueur in ("j1", "j2"):
            position, chemin = self.generaux.trouver_position_general(joueur, "general1", self.profil)
            self.assertEqual(position, "village")
            self.assertEqual(chemin, self.chemin(joueur, reserve=True))

    def test_duplication_entre_reserve_et_garnison(self):
        reserve = self.general(reserve=True)
        garnison = self.general()
        occurrences = self.generaux.trouver_toutes_positions_general("j1", "general1", self.profil)
        self.assertEqual({o["chemin"] for o in occurrences}, {reserve, garnison})
        self.audit()
        self.assertFalse(reserve.exists())
        self.assertFalse(garnison.exists())
        self.assertTrue(self.chemin(territoire="repli").is_dir())
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "repli"})
        self.assertEqual(self.etat.lire_compteur_general("j1"), 1)

    def test_faux_generaux_supprimes_dans_les_deux_zones(self):
        chemins = []
        for reserve in (False, True):
            for nom in ("general01", "general2"):
                chemin = self.chemin(nom=nom, reserve=reserve)
                self.generaux.creer_general(chemin, nom)
                chemins.append(chemin)
        self.audit()
        self.assertTrue(all(not chemin.exists() for chemin in chemins))
        self.assertEqual(self.etat.charger_positions_generaux(), {})

    def test_proprietaire_reel_verifie_dans_reserve_et_garnison(self):
        for numero, reserve in enumerate((True, False), 1):
            nom = f"general{numero}"
            general = self.general("j1", nom, reserve=reserve)
            mauvais = self.chemin("j2", nom, reserve=reserve)
            general.rename(mauvais)
            self.proprietaires[mauvais] = "j1"
            self.audit()
            self.assertFalse(mauvais.exists())
            self.assertTrue(self.chemin("j1", nom, "repli").is_dir())
            self.assertEqual(self.etat.charger_positions_generaux()[f"j1:{nom}"], "repli")

    def test_identite_sans_position_officielle_refusee_meme_avec_compteur(self):
        self.etat.sauvegarder_compteur_general("j1", 1)
        copies = [self.chemin(reserve=reserve) for reserve in (False, True)]
        for chemin in copies:
            self.generaux.creer_general(chemin, "general1")
        self.audit()
        self.assertTrue(all(not chemin.exists() for chemin in copies))
        self.assertFalse(self.chemin(territoire="repli").exists())
        self.assertEqual(self.etat.charger_positions_generaux(), {})

    def test_passage_par_reserve_ne_permet_pas_de_sortir_du_home_plus_loin(self):
        home = self.general(territoire="home")
        reserve = self.chemin(reserve=True)
        home.rename(reserve)
        destination = self.chemin(territoire="est_1")
        reserve.rename(destination)
        self.audit()
        self.assertFalse(destination.exists())
        self.assertTrue(self.chemin(territoire="repli").exists())
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "repli"})

    def test_home_et_retour_repli_vers_village(self):
        home = self.general(territoire="home")
        reserve = self.chemin(reserve=True)
        home.rename(reserve)
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()["j1:general1"], "village")
        repli = self.general("j2", territoire="repli")
        garnison = self.chemin("j2", place="2")
        repli.rename(garnison)
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()["j2:general1"], "village")

    def test_destination_repli_volontaire_reste_interdite(self):
        resultat = self.mouvements.verifier_deplacement_general(
            "j1", "village", "repli", {}, self.profil)
        self.assertEqual(resultat[:2], (False, False))

    def test_marche_forcee_depuis_reserve_et_controle_ennemi(self):
        reserve = self.general(reserve=True)
        destination = self.chemin(territoire="est_2")
        reserve.rename(destination)
        self.config.controle_territoires_path.write_text("est_1=allies", encoding="utf-8")
        self.audit()
        self.assertTrue(destination.exists())
        self.assertEqual(self.etat.charger_generaux_fatigues(), {"j1:general1"})
        self.assertEqual(self.etat.charger_positions_generaux()["j1:general1"], "est_2")
        for controle, valide in (("j2", True), ("allies", True), ("neutre", True), ("bot", False)):
            resultat = self.mouvements.verifier_deplacement_general(
                "j1", "village", "est_2", {"est_1": controle}, self.profil)
            self.assertEqual(resultat[:2], (valide, valide))


if __name__ == "__main__":
    unittest.main()
