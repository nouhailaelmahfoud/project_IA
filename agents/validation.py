"""Validation du code migré. (Les tests de la Tâche 3 s'ajouteront ici.)"""
import ast


def validate_code(language: str, code: str) -> list:
    """Renvoie la liste des erreurs (liste vide = code valide)."""
    if language == "python":
        try:
            ast.parse(code)
        except SyntaxError as error:
            return [f"Erreur de syntaxe Python 3, ligne {error.lineno} : {error.msg}"]
    elif language == "php":
        from agents.php_support import validate_php
        return validate_php(code)
    return []
