"""Vagues Est et progression sur disque temporaire, droits Unix simulés."""
import contextlib
import importlib
import io
import random
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch


class VaguesEst(unittest.TestCase):
    def setUp(self):
        self.contextes = contextlib.ExitStack()
        self.addCleanup(self.contextes.close)
        self.racine = Path(self.contextes.enter_context(tempfile.TemporaryDirectory()))
        self.contextes.enter_context(patch.object(sys, "path", [
            str(Path(__file__).resolve().parents[1]), *sys.path]))
        self.contextes.enter_context(patch.dict(sys.modules))
        uids = {"root": 0, "j1": 1001, "j2": 1002}
        sys.modules["pwd"] = SimpleNamespace(
            getpwnam=lambda nom: SimpleNamespace(pw_uid=uids[nom]))
        sys.modules["grp"] = SimpleNamespace(
            getgrnam=lambda nom: SimpleNamespace(gr_gid=uids[nom]))
        noms = ("config", "etat", "rapports", "generaux", "mouvements",
                "securite", "combats", "plateau", "vagues", "survie")
        for nom in noms:
            sys.modules.pop(nom, None)
        for nom in noms:
            setattr(self, nom, importlib.import_module(nom))
        self.config.game_path = self.racine / "game"
        for nom, relatif in {
            "positions_generaux_path": "systeme/positions_generaux.txt",
            "fatigue_generaux_path": "systeme/fatigue_generaux.txt",
            "controle_territoires_path": "systeme/controle_territoires.txt",
            "repli_path": "repli", "rapport_long_path": "rapport/rapport_long.txt",
            "rapports_territoires_dir": "rapport/territoires",
        }.items():
            setattr(self.config, nom, self.config.game_path / relatif)
        self.profil = self.config.configuration_mode("survie")
        self.aleatoire = random.Random(42)
        self.generaux.random = random.Random(13)
        self.combats.random = random.Random(13)
        self.chown = self.contextes.enter_context(patch.object(self.survie.os, "chown", create=True))
        self.chmod = self.contextes.enter_context(patch.object(self.survie.os, "chmod"))
        # Toute recherche de home reste dans l'environnement temporaire.
        self.contextes.enter_context(patch.object(
            self.generaux, "Path", lambda chemin: self.racine / chemin.lstrip("/")))

    def composition(self, numero):
        return self.vagues.composer_vague_est(numero, self.aleatoire)

    def creer(self, numero):
        return self.survie.creer_vague_est(numero, self.profil, self.aleatoire)

    def phase(self, numero):
        return self.survie.preparer_phase_ennemie(numero, self.profil, self.aleatoire)

    def inventaire(self, territoire):
        return self.survie.inventorier_ennemis(self.config.game_path / territoire, self.profil)

    def par_territoire(self, vague):
        resultat = {}
        for general in vague:
            resultat.setdefault(general["territoire"], []).append(general)
        return resultat

    def effectifs(self, vague):
        return {territoire: [sum(b["nombre"] for b in g["blocs"].values()) for g in liste]
                for territoire, liste in self.par_territoire(vague).items()}

    def types(self, general):
        return {b["type"] for b in general["blocs"].values() if b["nombre"]}

    def test_compositions_exactes_vagues_1_a_10(self):
        attendus = {
            1: {"est_1": [5], "est_2": [5], "est_3": [5]},
            2: {"est_3": [10]}, 3: {"est_3": [15]}, 4: {"est_3": [10, 10]},
            5: {t: [20, 20] for t in ("est_1", "est_2", "est_3")},
            6: {"est_3": [20, 20]}, 7: {"est_3": [20, 20]},
            8: {"est_3": [20, 20]}, 9: {"est_2": [20, 20], "est_3": [20, 20]},
            10: {t: [20, 20] for t in ("est_1", "est_2", "est_3")},
        }
        for numero, attendu in attendus.items():
            with self.subTest(vague=numero):
                vague = self.composition(numero)
                self.assertEqual(self.effectifs(vague), attendu)
                if numero in (6, 7):
                    self.assertEqual(self.types(vague[-1]), {6: {"archer"}, 7: {"piquier"}}[numero])
                if numero in (8, 9):
                    for liste in self.par_territoire(vague).values():
                        self.assertEqual(len(self.types(liste[-1])), 1)

    def test_boss_5_cavaliers_avant_sur_chaque_territoire(self):
        for liste in self.par_territoire(self.composition(5)).values():
            self.assertEqual(len(liste), 2)
            self.assertEqual(liste[1]["blocs"]["avant"], {"nombre": 20, "type": "cavalier"})
            self.assertTrue(all(liste[1]["blocs"][bloc]["nombre"] == 0
                                for bloc in ("droite", "gauche", "arriere")))

    def test_patterns_11_a_25_et_boss_repetes(self):
        for debut, base in ((11, 2), (16, 3), (21, 4)):
            for decalage in range(5):
                numero = debut + decalage
                with self.subTest(vague=numero):
                    vague = self.composition(numero)
                    territoires = (("est_3",) if decalage < 3 else
                                   ("est_2", "est_3") if decalage == 3 else
                                   ("est_1", "est_2", "est_3"))
                    self.assertEqual(self.effectifs(vague), {t: [20] * (base + 1) for t in territoires})
                    for liste in self.par_territoire(vague).values():
                        if decalage < 2:
                            self.assertEqual(self.types(liste[-1]), [{"archer"}, {"piquier"}][decalage])
                        elif decalage < 4:
                            self.assertEqual(len(self.types(liste[-1])), 1)

    def test_regime_26_plus_y_compris_multiples_de_cinq(self):
        for numero in (26, 27, 28, 29, 30, 35, 100, 1001):
            with self.subTest(vague=numero):
                self.assertEqual(self.effectifs(self.composition(numero)),
                                 {t: [20] * 4 for t in ("est_1", "est_2", "est_3")})

    def test_tirages_reproductibles_varies_et_blocs_valides(self):
        a = self.vagues.composer_vague_est(26, random.Random(7))
        self.assertEqual(a, self.vagues.composer_vague_est(26, random.Random(7)))
        self.assertNotEqual(a, self.vagues.composer_vague_est(26, random.Random(8)))
        self.assertTrue(any(len(self.types(g)) > 1 for g in a))
        for numero in range(1, 31):
            for general in self.composition(numero):
                self.assertEqual(set(general["blocs"]), {"avant", "droite", "gauche", "arriere"})
                for bloc in general["blocs"].values():
                    self.assertGreaterEqual(bloc["nombre"], 0)
                    if bloc["nombre"]:
                        self.assertIn(bloc["type"], ("archer", "piquier", "cavalier"))
                    else:
                        self.assertIsNone(bloc["type"])

    def test_fiches_identites_et_affichage_persistants(self):
        chemins = self.creer(1) + self.creer(5)
        for index, chemin in enumerate(chemins, 1):
            self.assertEqual(chemin.name, f"general{index}")
            self.assertTrue(self.generaux.est_general_valide(chemin))
            fiche = self.generaux.lire_fiche_general(chemin)
            vague, rang = (1, index) if index <= 3 else (5, index - 3)
            self.assertEqual(fiche["nom"], chemin.name)
            self.assertEqual(fiche["faction"], "est")
            self.assertEqual(fiche["vague"], str(vague))
            self.assertEqual(fiche["nom_affichage"], f"general{vague}_{rang}")
            self.assertIsNone(self.generaux.numero_general_depuis_nom(fiche["nom_affichage"]))
        self.assertEqual(self.etat.lire_compteur_general("bot"), 9)
        self.assertEqual(len(self.etat.charger_positions_generaux()), 9)
        self.assertFalse(list(self.racine.rglob("ordre_surnombre.txt")))

    def test_permissions_root_recursives_700_600(self):
        chemins = self.creer(1)
        for chemin in chemins:
            for element in (chemin, *chemin.rglob("*")):
                self.assertIn(call(element, 0, 0), self.chown.call_args_list)
                self.assertIn(call(element, 0o700 if element.is_dir() else 0o600), self.chmod.call_args_list)
        for territoire in self.profil["territoires"]:
            for dossier in (territoire / "bot", *(z["chemin"] for z in
                            self.generaux.zones_generaux_territoire(territoire, "bot", self.profil))):
                self.assertIn(call(dossier, 0, 0), self.chown.call_args_list)
                self.assertIn(call(dossier, 0o700), self.chmod.call_args_list)

    def test_anciens_avancent_avant_creation_et_nouveaux_restent(self):
        self.phase(1)
        self.assertEqual(self.etat.charger_positions_generaux(), {
            "bot:general1": "est_1", "bot:general2": "est_2", "bot:general3": "est_3"})
        creer_reel = self.survie.creer_vague_est
        def verifier_puis_creer(*args):
            self.assertEqual(self.etat.charger_positions_generaux(), {
                "bot:general1": "village", "bot:general2": "est_1", "bot:general3": "est_2"})
            return creer_reel(*args)
        with patch.object(self.survie, "creer_vague_est", side_effect=verifier_puis_creer):
            phase = self.phase(2)
        self.assertEqual(len(phase["deplacements"]), 3)
        self.assertEqual(self.etat.charger_positions_generaux()["bot:general4"], "est_3")
        self.phase(3)
        self.assertEqual(self.etat.charger_positions_generaux(), {
            "bot:general1": "village", "bot:general2": "village", "bot:general3": "est_1",
            "bot:general4": "est_2", "bot:general5": "est_3"})

    def test_surnombre_conserve_toutes_unites_et_avance_aussi_les_renforts(self):
        self.creer(25)  # 5 par territoire, le cinquième attend physiquement.
        for territoire in ("est_1", "est_2", "est_3"):
            inventaire = self.inventaire(territoire)
            self.assertEqual(len(inventaire), 5)
            self.assertEqual(sum(self.generaux.total_general_depuis_chemin(g["chemin"]) for g in inventaire), 100)
            self.assertEqual(sum(g["emplacement"] is None for g in inventaire), 1)
            forces = self.generaux.lire_forces_territoire(self.config.game_path / territoire, self.profil)
            self.assertEqual(len(self.generaux.generaux_actifs_joueur(forces, "bot")), 4)
        self.phase(26)
        for territoire, nombre in (("village", 5), ("est_1", 9), ("est_2", 9), ("est_3", 4)):
            inventaire = self.inventaire(territoire)
            self.assertEqual(len(inventaire), nombre)
            self.assertEqual(sum(self.generaux.total_general_depuis_chemin(g["chemin"]) for g in inventaire), nombre * 20)
            for general in inventaire:
                self.assertEqual(self.generaux.trouver_position_general("bot", general["nom"], self.profil),
                                 (territoire, general["chemin"]))
        self.assertEqual(len(self.etat.charger_positions_generaux()), 27)
        for general in self.inventaire("est_1")[:4]:
            self.assertEqual(general["fiche"]["vague"], "25")
            self.assertIsNotNone(general["emplacement"])

    def test_audit_joueurs_conserve_identites_bot_et_renforts(self):
        self.creer(25)
        positions = self.etat.charger_positions_generaux()
        with contextlib.redirect_stdout(io.StringIO()):
            self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(self.etat.charger_positions_generaux(), positions)
        self.assertEqual(sum(len(self.inventaire(t)) for t in ("est_1", "est_2", "est_3")), 15)

    def test_compositions_materialisees_sans_nettoyage_ni_perte(self):
        for numero in range(1, 11):
            with self.subTest(vague=numero):
                chemins = self.survie.creer_vague_est(numero, self.profil, random.Random(15))
                attendus = self.vagues.composer_vague_est(numero, random.Random(15))
                for chemin, attendu in zip(chemins, attendus):
                    avant = set(chemin.rglob("*"))
                    blocs = self.generaux.lire_blocs_general(chemin)
                    for bloc, infos in attendu["blocs"].items():
                        self.assertEqual(blocs[bloc]["nombre"], infos["nombre"])
                        if infos["nombre"]:
                            self.assertEqual(blocs[bloc]["type"], infos["type"])
                    self.assertEqual(set(chemin.rglob("*")), avant)

    def test_rapport_combat_affiche_vague_et_garde_identite_technique(self):
        self.creer(2)
        territoire = self.config.game_path / "est_3"
        chemin = territoire / "j1/1/general1"
        chemin.parent.mkdir(parents=True)
        self.generaux.creer_general(chemin, "general1")
        unite = chemin / "avant/infanterie1"
        unite.mkdir()
        (unite / "arc").touch()
        forces = self.generaux.lire_forces_territoire(territoire, self.profil)
        with contextlib.redirect_stdout(io.StringIO()):
            resultat = self.combats.combat_entre_generaux(forces["allies"]["1"], forces["bot"]["1"])
            self.rapports.ecrire_ligne_affrontement_territoire(territoire, "1", resultat)
            self.rapports.ecrire_detail_engagement(territoire, "1", resultat)
        self.assertEqual(resultat["general_2"], "general1")
        self.assertEqual(resultat["affichage_2"], "general2_1")
        texte = (self.config.rapports_territoires_dir / "est_3.txt").read_text(encoding="utf-8")
        self.assertIn("bot general2_1", texte)
        self.assertIn("general2_1", self.config.rapport_long_path.read_text(encoding="utf-8"))
        self.assertEqual(self.etat.lire_compteur_general("bot"), 1)

    def test_numero_detruit_jamais_reutilise(self):
        chemin = self.creer(2)[0]
        for unite in list(chemin.glob("*/infanterie*")) + list(chemin.glob("*/cavalerie*")):
            for equipement in unite.iterdir():
                equipement.unlink()
            unite.rmdir()
        with contextlib.redirect_stdout(io.StringIO()):
            self.generaux.supprimer_general_si_vide({"chemin": chemin, "nom": chemin.name, "joueur": "bot"})
        self.assertNotIn("bot:general1", self.etat.charger_positions_generaux())
        self.assertEqual(self.creer(3)[0].name, "general2")

    def test_entrees_invalides_sans_effets_et_profil_classique_refuse(self):
        for numero in (0, -1, True, 1.5, "1"):
            with self.assertRaises(ValueError):
                self.phase(numero)
        with self.assertRaises(ValueError):
            self.survie.preparer_phase_ennemie(1, self.config.configuration_mode("classique"))
        self.assertFalse(self.config.game_path.exists())

    def ajouter_ennemi_colonne(self, numero, territoire="est_3"):
        self.survie.preparer_zones_bot(self.profil)
        territoire = self.config.game_path / territoire
        chemin = self.survie.destination_ennemi(territoire, f"general{numero}", self.profil)
        self.generaux.creer_general(chemin, chemin.name)
        unite = chemin / "avant/infanterie1"
        unite.mkdir()
        (unite / "pique").touch()
        self.generaux.donner_permissions_general(chemin, "root")
        self.survie.enregistrer_arrivee_ennemi(territoire, chemin, self.profil)
        positions = self.etat.charger_positions_generaux()
        positions[f"bot:{chemin.name}"] = territoire.name
        self.etat.sauvegarder_positions_generaux(positions)
        self.etat.sauvegarder_compteur_general("bot", max(numero, self.etat.lire_compteur_general("bot")))
        return chemin

    def detruire_ennemi_colonne(self, chemin):
        (chemin / "avant/infanterie1/pique").unlink()
        (chemin / "avant/infanterie1").rmdir()
        with contextlib.redirect_stdout(io.StringIO()):
            self.generaux.supprimer_general_si_vide({
                "chemin": chemin, "nom": chemin.name, "joueur": "bot"})

    def test_quatre_actifs_detruits_six_renforts_remontent_sans_combat_en_cascade(self):
        for numero in range(1, 11):
            self.ajouter_ennemi_colonne(numero)
        territoire = self.config.game_path / "est_3"
        joueur = territoire / "j1/1/general1"
        joueur.parent.mkdir(parents=True)
        self.generaux.creer_general(joueur, joueur.name)
        for numero in range(20):
            unite = joueur / "avant" / f"infanterie{numero + 1}"
            unite.mkdir()
            (unite / "arc").touch()
        with contextlib.redirect_stdout(io.StringIO()):
            self.combats.resoudre_combat_v15(territoire, self.profil)
        inventaire = self.inventaire("est_3")
        self.assertEqual([g["nom"] for g in inventaire], [f"general{i}" for i in range(5, 11)])
        self.assertEqual([g["emplacement"] for g in inventaire], ["1", "2", "3", "4", None, None])
        self.assertEqual(sum(self.generaux.total_general_depuis_chemin(g["chemin"]) for g in inventaire), 6)
        journal = self.config.rapport_long_path.read_text(encoding="utf-8")
        self.assertEqual(journal.count("Engagement :"), 4)
        self.assertIn("Contrôle après remontée : conteste", journal)
        self.assertEqual(self.etat.lire_compteur_general("bot"), 10)
        # Le joueur part : la colonne entière avance ensuite, aucun renfort abandonné.
        depart = self.config.game_path / "est_2/j1/1"
        depart.mkdir(parents=True)
        joueur.rename(depart / joueur.name)
        self.survie.avancer_ennemis(self.profil)
        self.assertEqual(self.inventaire("est_3"), [])
        self.assertEqual([g["nom"] for g in self.inventaire("est_2")],
                         [f"general{i}" for i in range(5, 11)])
        self.assertEqual(set(self.etat.charger_positions_generaux().values()), {"est_2"})

    def test_colonne_suit_positions_puis_arrivee_pas_numeros(self):
        for numero in range(10, 0, -1):
            self.ajouter_ennemi_colonne(numero)
        territoire = self.config.game_path / "est_3"
        attendus = [f"general{i}" for i in range(10, 0, -1)]
        self.assertEqual([g["nom"] for g in self.inventaire("est_3")], attendus)
        ordre = territoire / "bot/renforts/ordre_arrivee.txt"
        self.assertEqual(ordre.read_text(encoding="utf-8").splitlines(), attendus[4:])
        self.assertIn(call(ordre, 0, 0), self.chown.call_args_list)
        self.assertIn(call(ordre, 0o600), self.chmod.call_args_list)
        self.survie.avancer_ennemis(self.profil)
        self.assertEqual([g["nom"] for g in self.inventaire("est_2")], attendus)
        self.assertEqual(self.inventaire("est_3"), [])
        self.survie.avancer_ennemis(self.profil)
        self.survie.avancer_ennemis(self.profil)
        self.assertEqual([g["nom"] for g in self.inventaire("village")], attendus)
        self.assertEqual([g["emplacement"] for g in self.inventaire("village")],
                         ["1", "2", "3", "4"] + [None] * 6)
        self.assertEqual(set(self.etat.charger_positions_generaux().values()), {"village"})

    def test_places_partiellement_vides_et_renfort_mort_ignore(self):
        chemins = [self.ajouter_ennemi_colonne(i) for i in range(1, 9)]
        self.detruire_ennemi_colonne(chemins[0])
        self.detruire_ennemi_colonne(chemins[2])
        # Un dossier vide encore présent ne doit pas être promu.
        (chemins[4] / "avant/infanterie1/pique").unlink()
        (chemins[4] / "avant/infanterie1").rmdir()
        with contextlib.redirect_stdout(io.StringIO()):
            promus = self.generaux.remonter_renforts_bot(self.config.game_path / "est_3", self.profil)
        self.assertEqual([p.name for p in promus], ["general6", "general7"])
        self.assertEqual([g["nom"] for g in self.inventaire("est_3")],
                         ["general6", "general2", "general7", "general4", "general8"])
        self.assertNotIn("bot:general5", self.etat.charger_positions_generaux())
        self.assertEqual(self.generaux.remonter_renforts_bot(self.config.game_path / "est_3", self.profil), [])

    def test_arrivees_rejoignent_derriere_colonne_presente(self):
        for numero in range(10, 16):
            self.ajouter_ennemi_colonne(numero, "village")
        for numero in (1, 2, 3):
            self.ajouter_ennemi_colonne(numero, "est_1")
        self.detruire_ennemi_colonne(self.config.game_path / "village/bot/1/general10")
        self.survie.avancer_ennemis(self.profil)
        inventaire = self.inventaire("village")
        self.assertEqual([g["nom"] for g in inventaire],
                         ["general14", "general11", "general12", "general13",
                          "general15", "general1", "general2", "general3"])
        self.assertEqual(self.inventaire("est_1"), [])


if __name__ == "__main__":
    unittest.main()
