from typing import TypedDict


class MigrationState(TypedDict):
    language: str          # "python" (bientôt "php")
    mode: str              # "hybrid", "rules_only" ou "llm_only"
    llm_analyzer: bool     # le LLM analyse aussi (en plus des détecteurs)
    use_detectors: bool    # les détecteurs fixes sont-ils utilisés ?
    file_path: str
    original_code: str     # le code d'origine, jamais modifié
    current_code: str      # le code en cours de migration
    rules_code: str        # le code après les règles (version sûre)
    rolled_back: bool      # True si les modifications du modèle ont été écartées
    issues: list           # problèmes détectés par la Tâche 1
    risks: list            # risques repérés par l'Analyseur
    errors: list           # erreurs de validation
    review_problems: list  # problèmes signalés par le Reviewer
    approved: bool
    iteration: int         # nombre de passages du Migrateur
    max_iterations: int
    llm_calls: int
    tokens_in: int
    tokens_out: int
    log: list
    verify: bool           #  tests dans Docker activés ?
    tests: str             #  tests écrits avant la migration (peut être vide)
    verification: dict     #  dernier résultat de verify() (erreurs, métriques)
