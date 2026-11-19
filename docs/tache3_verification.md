# Tâche 3 : moteur de vérification et tests

## Principe

Pour chaque fichier migré, `verification.engine.verify()` :

1. **Analyse statique** du code migré (Python 3.12 / PHP 8.3) : ruff et `php -l` (bloquants),
   pylint, mypy et PHPStan (avertissements ; PHPStan est bloquant pour les fonctions
   disparues, comme `mysql_connect`).
2. **Comportement** : l'original s'exécute dans son ancien environnement (Python 2.7 / PHP 7.4),
   le migré dans le nouveau. Les sorties doivent être identiques.
3. **Tests de caractérisation** (facultatif) : écrits par le LLM AVANT la migration, gardés
   seulement s'ils passent sur l'original (pytest / PHPUnit), puis rejoués sur le migré.

Les erreurs repartent au Migrateur (boucle de validation du pipeline, `--max-iterations`).

Pour Python, deux différences purement cosmétiques entre Python 2 et Python 3 sont retirées de
la sortie de l'original avant la comparaison : le suffixe des entiers longs (`300L` devient `300`)
et le préfixe des chaînes (`u'a'` devient `'a'`). Sans cela, une migration correcte serait
signalée comme une régression.

## Environnements Docker

| Image | Rôle |
|---|---|
| smartmigrator-py27 / php74 | legacy : exécute l'original |
| smartmigrator-py312 / php83 | modern : exécute le migré, analyse statique, couverture |

Le code inconnu tourne sans réseau, avec limites de mémoire, de CPU et de processus.
Les images se construisent avec `build-images` (ou automatiquement au premier usage).

## Utilisation

~~~bash
python3 -m verification.run_verification build-images
python3 -m verification.run_verification regenerate-expected --dry-run
python3 -m verification.run_verification regenerate-expected
python3 -m verification.run_verification check python original.py migre.py

python3 run_agents.py python samples/py2_corpus/bank/bank.py --mode rules_only --verify
python3 run_agents.py python samples/py2_corpus/bank/bank.py --mode hybrid --provider openrouter --verify --generate-tests
python3 run_agents.py php samples/php7_corpus/blog/blog.php --mode hybrid --provider openrouter --verify --generate-tests

python3 -m eval.run_benchmark --docker --modes rules_only llm_only hybrid-sans-detecteurs hybrid --provider openrouter
~~~

Sous Windows (PowerShell), remplacer `python3` par `python`.

Les tests de la Tâche 3 n'ont pas besoin de Docker (un faux exécuteur remplace Docker) :

~~~bash
python3 -m pytest tests/test_verification.py -q
~~~

## Sorties attendues du corpus

`regenerate-expected` exécute chaque programme d'origine dans Python 2.7 ou PHP 7.4 et compare
sa vraie sortie aux fichiers de `eval/expected/`. Les programmes qui ne s'exécutent pas seuls
(base de données, locale) sont ignorés. Résultat actuel : `bank`, `inventory`, `textstats` et
`blog` sont identiques aux sorties attendues ; `legacy_db` est ignoré (`mysql_connect`) ;
`shop` a été ajouté (`eval/expected/php/shop.txt`).

## Métriques

Chaque exécution avec `--verify` écrit `eval/results/verification_<date>.json` et `.md` :
taux de réussite, couverture, nombre d'itérations, retours arrière, avertissements.

## Limites connues

- Sans Docker, `verify()` ne bloque rien et le signale (« tests non exécutés »).
- Les programmes qui demandent une base de données ou une locale ne sont pas comparés.
- La couverture PHP dépend de pcov et de PHPUnit 10 (essai « au mieux »).
- La normalisation Python 2 → 3 est volontairement limitée aux suffixes `L` et `u` ;
  d'autres différences (ordre des dictionnaires, par exemple) restent signalées.