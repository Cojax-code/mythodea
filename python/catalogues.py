"""Identifiants permanents et définitions ; aucun accès au plateau.

Ne jamais recycler un identifiant supprimé. La valeur de fabrication est une
référence documentaire, distincte de la valeur de combat individuelle.
"""

UNITES = {
    1: dict(nom='archer', prefixe='infanterie', recette=('arc',), fabrication=5, valeur_combat=5,
            etiquettes=('infanterie', 'distance'), forces=('piquier',),
            faiblesses=('cavalier', 'cavalerie_lourde'), effets=(), natures=None,
            terrain=None, positionnement=None, progression=False),
    2: dict(nom='piquier', prefixe='infanterie', recette=('pique',), fabrication=5, valeur_combat=5,
            etiquettes=('infanterie',), forces=('cavalier', 'cavalerie_lourde'),
            faiblesses=('archer',), effets=(), natures=None,
            terrain=None, positionnement=None, progression=False),
    3: dict(nom='cavalier', prefixe='cavalerie', recette=('cheval',), fabrication=5, valeur_combat=5,
            etiquettes=('cavalerie',), forces=('archer',),
            faiblesses=('piquier', 'cavalerie_lourde'), effets=(), natures=None,
            terrain=None, positionnement=None, progression=False),
    4: dict(nom='cavalerie_lourde', prefixe='cavalerie_L',
            recette=('cheval', 'armure', 'cuirasse', 'bouclier', 'casque'), fabrication=None, valeur_combat=5,
            etiquettes=('cavalerie', 'lourde'), forces=('archer', 'cavalier'),
            faiblesses=('piquier',), effets=('formation_avant_15',), natures=None,
            terrain=None, positionnement=None, progression=False),
}

# Les jetons historiques ordre.txt restent valides et ne sont pas ces IDs.
ORDRES = {
    1001: dict(jeton='1-1', nom='retraite_apres_premiere_manche', categorie='globale',
               disponible=False, contre=False, progression=False),
    1002: dict(jeton='1-2', nom='attaque_frontale', categorie='globale',
               disponible=True, contre=False, progression=True),
    1003: dict(jeton='2-1', nom='attaque_chirurgicale', categorie='duel',
               disponible=False, contre=False, progression=False),
    1004: dict(jeton='2-2', nom='pluie_de_fleches', categorie='duel',
               disponible=False, contre=False, progression=False),
    1005: dict(jeton='3-1', nom='fuir_avant_la_mort', categorie='individuelle',
               disponible=False, contre=False, progression=False),
}

# 101..199 : apprentissages d'unités ; 201..299 : catégories de caractéristiques.
# 1001..1999 : ordres. Un ID d'unité et un ID d'évolution ne sont pas interchangeables.
EVOLUTIONS = {
    101: dict(categorie='unite', cible=1, disponible=False, natures=None),
    102: dict(categorie='unite', cible=2, disponible=False, natures=None),
    103: dict(categorie='unite', cible=3, disponible=False, natures=None),
    104: dict(categorie='unite', cible=4, disponible=True, natures=('instinctif',)),
    201: dict(categorie='commandement', cible=None, disponible=True, natures=('stratege',)),
    202: dict(categorie='moral', cible=None, disponible=True, natures=('instinctif',)),
    **{identifiant: dict(categorie='ordre', cible=identifiant,
                         disponible=ordre['progression'],
                         natures=('stratege',) if ordre['categorie'] == 'globale' else None)
       for identifiant, ordre in ORDRES.items()},
}

UNITE_PAR_NOM = {definition['nom']: identifiant for identifiant, definition in UNITES.items()}


def valeur_combat(type_unite):
    """Valeur individuelle officielle ; ni coût, ni donnée de la fiche joueur."""
    valeur = UNITES[UNITE_PAR_NOM[type_unite]].get('valeur_combat')
    if type(valeur) is not int or valeur <= 0:
        raise ValueError('La valeur de combat doit être un entier strictement positif.')
    return valeur


def verifier_catalogues():
    if len(UNITE_PAR_NOM) != len(UNITES) or set(UNITES) & set(EVOLUTIONS):
        raise ValueError('Identifiants ou noms de catalogue ambigus.')
    if any(type(i) is not int or i <= 0 for i in (*UNITES, *EVOLUTIONS)):
        raise ValueError('Les identifiants permanents sont des entiers positifs.')
    for definition in UNITES.values():
        valeur_combat(definition['nom'])


verifier_catalogues()
