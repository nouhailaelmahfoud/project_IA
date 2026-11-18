# Comment ajouter un nouveau langage

Exemple : migration d'un langage `X` (ancienne version vers nouvelle version).

## 1. Le plugin d'analyse (Tâche 1)

Créer `plugins/x_analyzer/` avec une classe qui hérite de `LanguagePlugin` (`core/plugin_base.py`),
définit `name`, `file_extensions` et `analyze_file()`, et renvoie des objets `Issue` (`core/models.py`).

## 2. Les règles automatiques

Écrire une fonction `apply_x_rules(source) -> RulesResult` (voir `agents/rules_engine.py`
et `agents/php_support.py`). Elle doit rendre le code d'origine, avec un avertissement,
si l'outil n'est pas installé ou échoue.

## 3. Les détecteurs

Écrire `detect_x_risks(code, original=None) -> list` qui renvoie des dictionnaires :
`kind`, `line`, `code`, `description`, `suggestion`, `blocking`.
Un risque `blocking` doit disparaître avant que le résultat soit accepté.

## 4. La validation

Ajouter une branche `x` dans `agents/validation.py` : renvoyer la liste des erreurs
(liste vide si le code est valide).

## 5. Les consignes des agents

Créer `prompts/x_to_y/` avec `analyzer.md`, `migrator.md` et `reviewer.md`
(copier ceux de `prompts/py2_to_3/` ou `prompts/php7_to_8/` et les adapter).

## 6. L'enregistrer

Dans `agents/languages.py`, ajouter une entrée :

~~~python
"x": {
    "prompt_dir": "x_to_y",
    "target": "Y",
    "rules": apply_x_rules,
    "detector": detect_x_risks,
},
~~~

## 7. Brancher le lanceur et l'évaluation

- `run_agents.py` : ajouter `"x"` dans les choix du premier argument.
- `eval/run_benchmark.py` : ajouter un corpus `"x"` dans `CORPORA` et la branche d'évaluation.

## 8. Tester

Ajouter un test avec un faux modèle (voir `tests/test_pipeline.py` et `tests/test_php.py`)
puis lancer `python3 -m pytest tests -q`.
