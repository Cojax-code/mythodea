# Base de données Mythodea — fondation V0.1

Cette première structure PostgreSQL prépare la base commune de Mythodea sans modifier le gameplay actuel.

## Principe important

Pour la V2.0 actuelle, le système de fichiers Linux reste la source officielle du jeu :

- les généraux restent des dossiers ;
- les unités restent représentées sur le disque ;
- les déplacements restent des déplacements réels de dossiers ;
- les permissions Unix, l'anti-triche et les états sous `/game` restent inchangés.

PostgreSQL est introduit d'abord pour :

1. le simulateur web ;
2. les historiques structurés de combats ;
3. les statistiques ;
4. les futurs écrans de consultation ;
5. une éventuelle migration progressive de certaines données plus tard.

Le moteur Python reste la source des règles de combat. La base ne doit pas réimplémenter ces règles.

## Fichiers

- `001_initial_schema.sql` : tables et relations.
- `002_seed_reference.sql` : catalogue initial provenant du moteur V2.0.

## Trois groupes de données

### Catalogue

Tables relativement stables :

- `unit_types`
- `order_types`
- `weather_types`
- `terrain_types`

Les terrains sont volontairement laissés sans données initiales : le panneau terrain du simulateur est prévu, mais leurs effets de gameplay ne sont pas encore définis.

### Partie réelle / future persistance

Tables prévues pour représenter proprement une partie :

- `games`
- `actors`
- `territories`
- `territory_connections`
- `generals`
- `general_blocks`
- `block_units`
- `general_orders`
- `turns`

Elles ne remplacent pas encore les fichiers actuels du Raspberry Pi.

### Simulateur web

Tables dédiées :

- `simulations`
- `simulation_participants`
- `simulation_blocks`
- `combat_events`

Une simulation conserve notamment :

- la version / le commit du moteur ;
- une graine aléatoire éventuelle ;
- la météo et le terrain ;
- les généraux et leurs quatre blocs ;
- les résultats ;
- un journal chronologique ordonné.

`input_snapshot` et `result_snapshot` sont en JSONB afin de conserver exactement les entrées/sorties du moteur même si l'interface évolue.

## Installation locale simple

Exemple avec PostgreSQL déjà installé :

```bash
createdb mythodea
psql -d mythodea -f database/001_initial_schema.sql
psql -d mythodea -f database/002_seed_reference.sql
```

Vérification :

```bash
psql -d mythodea
```

Puis :

```sql
SET search_path TO mythodea, public;
\dt
SELECT * FROM unit_types;
SELECT * FROM order_types;
SELECT * FROM weather_types;
```

## Étape suivante prévue

La prochaine étape logique est un petit adaptateur Python PostgreSQL, séparé du moteur de combat, permettant au simulateur web de :

1. recevoir une configuration ;
2. créer un enregistrement de simulation ;
3. appeler le vrai moteur Python ;
4. sauvegarder le résultat et les événements ;
5. renvoyer le résultat au site.

Aucune règle de combat ne doit être recopiée en JavaScript ou en SQL.
