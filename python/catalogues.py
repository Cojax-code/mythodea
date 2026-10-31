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
            faiblesses=('distance',), effets=(), natures=None,
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

# Les quatre représentations historiques restent inchangées. Les nouveaux types
# ne donnent aucun droit de fabrication : le scanner authentifie leur origine.
UNITES.update({
    5: dict(nom='sauvageon', prefixe='sauvageon', recette=('sauvageon.txt',),
            valeur_combat=3, etiquettes=('humain', 'melee', 'a_pied', 'cruelle'),
            forces=(), faiblesses=('archer', 'cavalier', 'cavalerie_lourde'),
            effets=('regeneration_fuite',), natures=None, blessures=0, soins=None),
    6: dict(nom='chevalier_clinquant', prefixe='chevalier_clinquant', recette=(),
            valeur_combat=5, valeur_avant=6,
            etiquettes=('humain', 'melee', 'a_pied', 'noble', 'ami_des_animaux', 'armure_legere'),
            forces=('piquier', 'sauvageon'), faiblesses=('cavalier', 'archer', 'cavalerie_lourde'),
            effets=('moral_par_unite',), natures=('instinctif',), blessures=2, soins='hopital',
            tours_soins=2),
    7: dict(nom='orc_assaillant', prefixe='orc_assaillant', recette=('tome_du_orc_assaillant',),
            valeur_combat=6, valeur_avant=7, etiquettes=('orc', 'melee', 'cruelle', 'mauvais_nageur'),
            forces=('archer', 'piquier', 'cavalier'),
            faiblesses=('chevalier_clinquant', 'cavalerie_lourde', 'orc_chaman'),
            effets=(), natures=('instinctif',), blessures=1, soins='chaman'),
    8: dict(nom='orc_archer', prefixe='orc_archer', recette=('tome_du_orc_archer',),
            valeur_combat=6, etiquettes=('orc', 'distance', 'cruelle', 'mauvais_nageur'),
            forces=('piquier', 'sauvageon'),
            faiblesses=('chevalier_clinquant', 'cavalerie_lourde', 'cavalier', 'orc_chaman'),
            effets=(), natures=('instinctif',), blessures=1, soins='chaman'),
    9: dict(nom='orc_chaman', prefixe='orc_chaman', recette=('tome_du_orc_chaman',),
            valeur_combat=2, etiquettes=('orc', 'cruelle', 'mauvais_nageur', 'chaman', 'soutien'),
            forces=('orc_assaillant', 'orc_archer'), multiplicateur=3,
            faiblesses=('non_orc',), effets=('moral_cruel', 'soins_victoire'),
            natures=('instinctif',), blessures=1, soins='chaman'),
    10: dict(nom='messager_du_QG', prefixe='messager_du_QG',
             recette=('sceau du roi', 'enveloppe', 'monocle'), valeur_combat=0,
             etiquettes=('soutien', 'humain', 'non_combattant', 'a_pied'),
             forces=(), faiblesses=(), effets=('ordres_qg',), natures=('stratege',),
             blessures=0, soins=None),
    11: dict(nom='zombie', prefixe='zombi', recette=(), valeur_combat=5,
             etiquettes=('mort_vivant', 'sans_cerveau', 'propagation', 'mauvais_nageur', 'infatigable'),
             forces=(), faiblesses=('tout',), effets=(), natures=None, blessures=0, soins=None),
    12: dict(nom='Trop_gros_zombie', prefixe='Trop_gros_zombie', recette=(), valeur_combat=250,
             etiquettes=('mort_vivant', 'sans_cerveau', 'propagation', 'mauvais_nageur',
                         'infatigable', 'bouclier_vivant', 'spore'),
             forces=(), faiblesses=('tout',), effets=('sans_degats', 'bouclier_vivant'),
             natures=None, blessures=0, soins=None, places=10),
})
for identifiant, unite in UNITES.items():
    unite.setdefault('fabrication', None)
    unite.setdefault('terrain', None)
    unite.setdefault('positionnement', None)
    unite.setdefault('progression', identifiant in range(5, 11))
    unite.setdefault('blessures', 1)
    unite.setdefault('soins', 'hopital')
    unite.setdefault('tours_soins', 1)
    unite.setdefault('places', 1)

# Les anciens ordres tactiques sont abandonnés.
# Les configurations de terrain sont indépendantes des généraux.
ORDRES = {}

# 101..199 : apprentissages d'unités ; 201..299 : catégories de caractéristiques.
# 1001..1999 : ordres. Un ID d'unité et un ID d'évolution ne sont pas interchangeables.
EVOLUTIONS = {
    101: dict(categorie='unite', cible=1, disponible=False, natures=None),
    102: dict(categorie='unite', cible=2, disponible=False, natures=None),
    103: dict(categorie='unite', cible=3, disponible=False, natures=None),
    104: dict(categorie='unite', cible=4, disponible=True, natures=('instinctif',)),
    **{100 + i: dict(categorie='unite', cible=i, disponible=True, natures=UNITES[i]['natures'])
       for i in range(5, 11)},
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
    definition = UNITES[UNITE_PAR_NOM[type_unite]]
    valeur = definition.get('valeur_combat')
    if (type(valeur) is not int or valeur < 0 or
            (valeur == 0 and 'non_combattant' not in definition['etiquettes'])):
        raise ValueError('Valeur de combat : entier strictement positif requis, ou zéro pour un non-combattant.')
    return valeur


def verifier_catalogues():
    if len(UNITE_PAR_NOM) != len(UNITES) or set(UNITES) & set(EVOLUTIONS):
        raise ValueError('Identifiants ou noms de catalogue ambigus.')
    if any(type(i) is not int or i <= 0 for i in (*UNITES, *EVOLUTIONS)):
        raise ValueError('Les identifiants permanents sont des entiers positifs.')
    for definition in UNITES.values():
        valeur_combat(definition['nom'])


verifier_catalogues()
