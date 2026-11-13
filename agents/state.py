from typing import TypedDict


class MigrationState(TypedDict):
    language: str          # "python" (bientôt "php")
    mode: str              # "hybrid", "rules_only" ou "llm_only"
    file_path: str
    original_code: str     # le code d'origine, jamais modifié
    current_code: str      # le code en cours de migration
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
