"""Observations locales au worker : fonctions originales appelées une seule fois.

Aucune règle de résolution, écriture de partie ou consommation aléatoire ici.
Les annotations se placent entre les lignes du rapport intégral inchangé.
"""
import copy


class CombatObserver:
    def __init__(self, config, combats, generaux):
        self.config, self.combats, self.generaux = config, combats, generaux
        self.engagements, self.explanations = [], []
        self.frontal = False
        self.previous_targets = {}
        self.target_decision = None
        self.originals = {}
        self.calculations = []
        self.morale = []

    def annotate(self, kind, title, text, **facts):
        path = self.config.rapport_long_path
        line = path.read_text(encoding="utf-8").count("\n") if path.exists() else 0
        self.explanations.append({"line": line, "kind": kind, "title": title, "text": text, **facts})

    def __enter__(self):
        for name, wrapper in (("resoudre_attaque_frontale", self.front),
                              ("combat_entre_generaux", self.duel),
                              ("ordre_actions_manoeuvre", self.actions),
                              ("choisir_cible", self.target),
                              ("attaque_ciblee", self.attack),
                              ('combat_bloc', self.block),
                              ('supprimer_unites', self.casualties)):
            self.originals[name] = getattr(self.combats, name)
            setattr(self.combats, name, wrapper)
        return self

    def __exit__(self, *_):
        for name, original in self.originals.items():
            setattr(self.combats, name, original)

    def front(self, *args, **kwargs):
        self.frontal = True
        try:
            return self.originals["resoudre_attaque_frontale"](*args, **kwargs)
        finally:
            self.frontal = False

    def duel(self, one, two):
        self.previous_targets = {}
        phase = "frontal" if self.frontal else "range"
        reason = ("La configuration du territoire déclenche les duels entre positions correspondantes."
                  if self.frontal else
                  "Le combat rangé oppose les premiers généraux encore actifs dans l’ordre des positions 1 → 4 ; un survivant peut donc combattre à nouveau.")
        participants = [{"owner": g["joueur"], "name": g["nom"], "position": int(g["emplacement"])} for g in (one, two)]
        self.annotate("engagement", f"Pourquoi {one['joueur']} {one['nom']} affronte {two['joueur']} {two['nom']} ?", reason,
                      phase=phase, participants=participants)
        before = [self.generaux.lire_composition_general(g["chemin"]) for g in (one, two)]
        result = self.originals["combat_entre_generaux"](one, two)
        entry = copy.deepcopy(result)
        entry.update(phase=phase, participants=participants, before_blocks=before,
                     after_blocks=[self.generaux.lire_composition_general(g["chemin"]) for g in (one, two)])
        self.engagements.append(entry)
        return result

    def actions(self, army, initiative):
        actions = self.originals["ordre_actions_manoeuvre"](army, initiative)
        self.annotate("order", "Pourquoi cet ordre de manœuvre ?",
                      "Priorités : avant libre au choc, arrière, flancs par effectif décroissant (égalité départagée au hasard), puis avant ayant participé au choc initial. Cet avant peut agir dès la fin du premier tour de manœuvre s’il survit ; chaque bloc agit au plus une fois par tour de manœuvre, et les blocs vides sont exclus.",
                      actions=copy.deepcopy(actions), initiative=copy.deepcopy(initiative))
        return actions

    def target(self, army, attacker, unit_type):
        target = self.originals["choisir_cible"](army, attacker, unit_type)
        enemy = self.combats.adversaire_du_duel(army, attacker)
        candidates = [{"block": block, "count": army[enemy][block]["nombre"],
                       "advantage": self.combats.multiplicateur(unit_type, army[enemy][block]["type"])}
                      for block in self.config.ordre_blocs if army[enemy][block]["nombre"] > 0]
        self.target_decision = {"target": target, "candidates": candidates}
        return target

    def attack(self, army, attacker, defender, block, target):
        decision = self.target_decision
        # Ne pas expliquer si l'action n'est pas celle du choix observé.
        if decision and decision["target"] == target:
            selected = next(c for c in decision["candidates"] if c["block"] == target)
            reason = (f"Première cible non vide avec avantage de type (×{selected['advantage']}) dans l’ordre avant → droite → gauche → arrière."
                      if selected["advantage"] > 1 else
                      "Aucune cible avec avantage de type : le moteur choisit le bloc non vide le moins nombreux, puis l’ordre avant → droite → gauche → arrière en cas d’égalité.")
            key = (attacker["joueur"], block)
            previous = self.previous_targets.get(key)
            if previous and previous != target:
                empty = army[defender["joueur"]][previous]["nombre"] == 0
                reason += (f" L’ancienne cible {previous} est désormais vide." if empty else
                           f" La cible précédente était {previous} ; le choix est recalculé sur les effectifs actuels.")
            self.previous_targets[key] = target
            self.annotate("target", f"Pourquoi {attacker['joueur']} {attacker['nom']} {block} cible {target} ?",
                          reason, attacker=attacker["joueur"], general=attacker["nom"], block=block,
                          defender=defender["joueur"], defending_general=defender["nom"],
                          previous_target=previous, **copy.deepcopy(decision))
        self.target_decision = None
        return self.originals["attaque_ciblee"](army, attacker, defender, block, target)

    def explain_absences(self, generals, control):
        for camp, paths in generals.items():
            owner = "j1" if camp == "A" else "j2"
            for path in paths:
                participated = any(p["owner"] == owner and p["name"] == path.name
                                   for e in self.engagements for p in e["participants"])
                if not participated and control != "conteste":
                    self.annotate("absence", f"Camp {camp}, {path.name} : aucune participation",
                                  "Le moteur a terminé le combat avant d’engager ce général : les deux camps n’ont plus simultanément de forces actives.",
                                  owner=owner, general=path.name, position=int(path.parent.name), control=control)

    def block(self, infos_1, infos_2, fatigue_1=False, fatigue_2=False,
              bloc_1=None, bloc_2=None, fiche_1=None, fiche_2=None, *, general_1=None, general_2=None):
        entries = []
        for index, (info, enemy, block, fiche, adverse, general, opponent) in enumerate((
                (infos_1, infos_2, bloc_1, fiche_1, fiche_2, general_1, general_2),
                (infos_2, infos_1, bloc_2, fiche_2, fiche_1, general_2, general_1))):
            entries.append({'block': block, 'unit': info['type'], 'count': info['nombre'],
                'base': self.combats.valeur_base_bloc(info, block),
                'advantage': self.combats.multiplicateur(info['type'], enemy['type']),
                'bonus_percent': self.combats._bonus_valeur_duel(fiche, info['type'], index, general),
                'malus_percent': self.combats._malus_chaman_duel(adverse, info['type'], index, general, opponent)})
        self.calculations.append(entries)
        self.annotate('bonuses', 'Bonus appliqués par le moteur',
                      ' ; '.join(f"{e['block']} ({e['unit']}) : base {e['base']}, avantage ×{e['advantage']}, bonus personnel + QG {e['bonus_percent']} %, malus chaman {e['malus_percent']} %." for e in entries)
                      + ' Le moteur b31b842 conserve un plancher de valeur de 1 %.')
        return self.originals['combat_bloc'](infos_1, infos_2, fatigue_1, fatigue_2,
                bloc_1, bloc_2, fiche_1, fiche_2, general_1=general_1, general_2=general_2)

    def casualties(self, infos, survivors, general=None):
        # Observer le moral transmis à soldats.pertes : aucun recalcul local.
        original = self.combats.soldats.pertes
        def record(block, remaining, moral=0, aleatoire=None):
            self.morale.append({'general': general['nom'] if general else None,
                                'owner': general['joueur'] if general else None,
                                'unit': block['type'], 'morale': moral})
            self.annotate('morale', 'Moral effectif pour les sauvetages',
                          f"{general['joueur'] if general else ''} {general['nom'] if general else ''}, {block['type']} : moral effectif {moral}. La sélection et les blessures sont résolues par le moteur.")
            return original(block, remaining, moral, aleatoire)
        self.combats.soldats.pertes = record
        try:
            return self.originals['supprimer_unites'](infos, survivors, general)
        finally:
            self.combats.soldats.pertes = original
