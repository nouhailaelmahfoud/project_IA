# Tâche 2 : agents IA de refactoring

## Principe

Pour chaque fichier, le pipeline enchaîne :

1. **Règles automatiques** (2to3 pour Python, Rector pour PHP) : corrigent la syntaxe, gratuitement.
2. **Détecteurs fixes** : repèrent, sans IA, les pièges que les règles ne traitent pas
   (`__cmp__`, `cmp()`, `string.lower`, `file()`, divisions, `mysql_*`, `each()`...), avec le bon numéro de ligne.
3. **Migrateur (LLM)** : corrige seulement les pièges listés, en renvoyant des **modifications ciblées**
   (`<edit><old>...</old><new>...</new></edit>`) et non le fichier entier.
4. **Validation** : syntaxe (`ast` ou `php -l`) puis absence de pièges bloquants.
   En cas d'erreur, elle est renvoyée au Migrateur (nombre de tours limité).
5. **Reviewer (LLM)** : compare l'original et le résultat.
6. **Finalisation** : si les modifications ne sont pas validées, retour au code d'avant le Migrateur.

## Lancer

~~~bash
python3 run_agents.py python samples/py2_corpus/bank/bank.py --mode hybrid --provider openrouter
python3 run_agents.py php samples/php7_corpus/blog/blog.php --mode hybrid --provider ollama
~~~

Modes : `rules_only`, `llm_only`, `hybrid`. Options : `--max-iterations`, `--model`,
`--llm-analyzer`, `--no-detectors`.

## Configuration des modèles

Dans `.env` (jamais envoyé sur GitHub) : `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OLLAMA_MODEL`.
Réglages facultatifs : `OPENROUTER_MAX_TOKENS`, `OPENROUTER_REASONING_EFFORT`.

## Garde-fous

- Les risques signalés par un modèle sont vérifiés : la ligne de code citée doit exister dans le fichier.
- Un texte à remplacer ambigu ou introuvable est refusé et renvoyé au Migrateur.
- Une réponse coupée est réparée (JSON) ou signalée ; une erreur 429 est réessayée avec attente.
- Retour arrière si le Reviewer refuse ou si la validation échoue.

## Évaluation

~~~bash
python3 -m eval.run_benchmark --modes rules_only llm_only hybrid-sans-detecteurs hybrid --provider ollama
python3 -m eval.run_benchmark --language php --modes rules_only llm_only hybrid-sans-detecteurs hybrid --provider ollama
~~~

Les résultats (tableau `.md` et `.csv`) sont écrits dans `eval/results/`.
Les sorties attendues sont dans `eval/expected/`.

## Limites connues

- Le fichier entier est envoyé au modèle (pas de découpage en morceaux pour les gros fichiers).
- Sorties de référence Python déduites du comportement de Python 2, à confirmer avec la Tâche 3 (Docker).
- Les programmes PHP du corpus ne sont pas tous exécutables (base de données, locale).
- Peu de fichiers et un seul essai par cas : les résultats sont indicatifs.
