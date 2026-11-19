"""Validation du code migré : syntaxe, puis (Tâche 3) tests dans Docker."""
import ast


def validate_code(language: str, code: str, original: str = None,
                  file_path: str = "code", tests: str = "",
                  verify: bool = False, details: dict = None) -> list:
    """Renvoie la liste des erreurs (liste vide = code valide).

    Sans `verify`, seule la syntaxe est contrôlée (comportement d'origine).
    Avec `verify=True` et le code `original`, le moteur de la Tâche 3 lance
    l'analyse statique et les tests dans Docker ; le détail (avertissements,
    métriques) est alors copié dans `details`.
    """
    if language == "python":
        try:
            ast.parse(code)
        except SyntaxError as error:
            return [f"Erreur de syntaxe Python 3, ligne {error.lineno} : {error.msg}"]
    elif language == "php":
        from agents.php_support import validate_php
        errors = validate_php(code)
        if errors:
            return errors

    if verify and original is not None:
        from verification.engine import verify as run_verification
        result = run_verification(language, original, code, file_path, tests)
        if details is not None:
            details.update(result)
        return result["errors"]
    return []